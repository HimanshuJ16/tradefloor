"""Source/library/report invariants; no provider credentials or live model calls."""
import base64
import io
import json

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from tradefloor import desk, lab, library, reports, runs
from tradefloor.storage import connect


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADEFLOOR_HOME", str(tmp_path))


def source(**overrides):
    return library.ingest({"title": "Fictional earnings transcript", "source": "https://example.org/earnings.html", "rights": "MIT synthetic fixture", "kind": "text",
                           "published_at": "2026-09-27T12:00:00Z", "available_at": "2026-09-27T12:00:00Z", "content": "Demand strengthened. Cash flow reflects inventory spending. " * 45, **overrides})


def test_exact_spans_duplicate_identity_and_lexical_search():
    d = source()
    assert source()["id"] == d["id"]
    assert source()["duplicate"]
    stored = library.documents("get", d["id"])
    assert "original_base64" not in stored
    for c in stored["chunks"]:
        assert stored["text"][c["start"]:c["end"]] == c["text"]
    result = library.search("inventory cash", "2026-09-28T23:59:59Z")
    assert result["hits"][0]["eligible"]
    assert not library.search("unrelated")['hits']
    assert not library.search("cash", "2026-09-20T23:59:59Z")["hits"][0]["eligible"]


def test_html_is_text_and_excludes_executable_regions():
    d = source(kind="html", content='<h1>Cash flow</h1><script>alert("SECRET")</script><style>hidden</style><form>password</form><p>Revenue rose.</p>')
    body = library.documents("get", d["id"])["text"]
    assert "Cash flow" in body and "Revenue rose." in body
    assert all(value not in body for value in ("SECRET", "hidden", "password", "<script"))


def test_freeze_preserves_numerical_experiment_and_original_receipt():
    d = source()
    r = lab.simulate(worlds=100, sensitivity=False)
    parent = runs.read(r["run"]["run_id"])
    child = library.freeze(parent["id"], [{"document_id": d["id"], "chunk_id": d["chunks"][0]["id"]}])
    b = runs.read(child["run"]["run_id"])
    assert b["parent"] == parent["id"] and runs.read(parent["id"]) == parent
    assert b["inputs"]["prices"] == parent["inputs"]["prices"]
    assert b["result"]["scenario"] == parent["result"]["scenario"]
    added = b["inputs"]["evidence"][-1]
    assert added["anchor"]["document_text"][added["anchor"]["start"]:added["anchor"]["end"]] == added["text"]
    _, context = desk._context(b["id"])
    assert any(n["id"] == added["id"] for n in context["inspect_evidence"])
    assert all("anchor" not in n for n in context["inspect_evidence"])


@pytest.mark.parametrize("dates", [{"available_at": None}, {"published_at": None}, {"published_at": "2026-10-12T00:00:00Z", "available_at": "2026-10-12T00:00:00Z"}])
def test_unknown_or_later_source_cannot_be_frozen(dates):
    d = source(**dates)
    r = lab.simulate(worlds=100, sensitivity=False)
    with pytest.raises(ValueError, match="unknown or later"):
        library.freeze(r["run"]["run_id"], [{"document_id": d["id"], "chunk_id": d["chunks"][0]["id"]}])


def test_modified_document_is_not_silently_used():
    d = source()
    with connect(library.database()) as db:
        row = json.loads(db.execute("SELECT body FROM records WHERE id=?", (d["id"],)).fetchone()[0])
        row["text"] = "tampered"
        db.execute("UPDATE records SET body=? WHERE id=?", (json.dumps(row), d["id"]))
    with pytest.raises(ValueError, match="integrity"):
        library.search("cash")


def pdf(encrypted=False):
    writer = PdfWriter()
    page = writer.add_blank_page(300, 200)
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"), NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
    page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 100 Td (Fictional revenue rose; cash flow weakened.) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("test-only-password")
    target = io.BytesIO()
    writer.write(target)
    return target.getvalue()


def test_pdf_is_extracted_in_worker_with_exact_text_and_visible_failures():
    d = source(kind="pdf", file_base64=base64.b64encode(pdf()).decode())
    assert d["pages"] == 1 and "Fictional revenue rose" in d["chunks"][0]["text"]
    with pytest.raises(ValueError, match="extraction failed"):
        source(kind="pdf", file_base64=base64.b64encode(pdf(True)).decode())


@pytest.mark.parametrize("url", ["http://example.org/a", "https://user:pass@example.org/a", "https://example.org/a?token=secret", "https://127.0.0.1/a", "https://10.0.0.1/a", "https://localhost/a", "https://example.org:8443/a"])
def test_capture_rejects_private_or_credential_destinations(url):
    with pytest.raises(ValueError):
        library.public_url(url)


def test_dns_validation_and_connection_pin_the_same_public_address(monkeypatch):
    called = []
    monkeypatch.setattr(library.socket, "getaddrinfo", lambda *a, **k: [(None, None, None, None, ("8.8.8.8", 443))])
    class Socket:
        def close(self):
            pass
    monkeypatch.setattr(library.socket, "create_connection", lambda dest, **k: called.append(dest) or Socket())
    class Context:
        def wrap_socket(self, sock, server_hostname):
            called.append(server_hostname)
            return sock
    monkeypatch.setattr(library.ssl, "create_default_context", Context)
    class Response:
        status = 200
        def getheader(self, name, default):
            return "text/html" if name == "Content-Type" else default
        def read(self, size):
            if getattr(self, "done", False):
                return b""
            self.done = True
            return b"<p>Cash flow</p>"
    class Connection:
        def __init__(self, *a, **k):
            pass
        def request(self, *a, **k):
            self.connect()
        def getresponse(self):
            return Response()
        def close(self):
            pass
    monkeypatch.setattr(library, "HTTPSConnection", Connection)
    assert library._download("https://example.org/document")[1] == "html"
    assert called == [("8.8.8.8", 443), "example.org"]
    monkeypatch.setattr(library.socket, "getaddrinfo", lambda *a, **k: [(None, None, None, None, ("8.8.8.8", 443)), (None, None, None, None, ("127.0.0.1", 443))])
    with pytest.raises(ValueError, match="public Internet"):
        library.public_url("https://example.org/document", resolve=True)


def test_report_citations_escape_source_markup_and_omit_future_settlement():
    d = source(content='<img src="https://example.org/track"> Demand strengthened. [click](javascript:alert(1))')
    r = lab.simulate(worlds=100, sensitivity=False)
    child = library.freeze(r["run"]["run_id"], [{"document_id": d["id"], "chunk_id": d["chunks"][0]["id"]}])
    exported = reports.report(child["run"]["run_id"])
    assert "&lt;img" in exported["html"] and '<img src=' not in exported["html"]
    assert '<img src=' not in exported["markdown"]
    assert 'href="#source-1"' in exported["html"]
    assert "demo_settlement" not in json.dumps(exported)
    assert "synthetic_outcome" not in json.dumps(exported)
    assert any(s["span"] for s in exported["report"]["sources"])


def test_sec_discovery_builds_document_links_without_capture(monkeypatch):
    monkeypatch.setattr(library.timeline, "fetch", lambda *a: {"records": [{"published_at": "2026-09-27T12:00:00Z", "available_at": "2026-09-27T12:00:00Z", "value": {"company": "ACME", "form": "10-K", "accession": "0000320193-26-000001", "primary_document": "acme.htm", "filing_date": "2026-09-27"}}], "scope": "fixture"})
    row = library.discovery(body={"cik": "320193", "form": "10-K"})["sources"][0]
    assert row["url"] == "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/acme.htm"
    assert library.documents()["documents"] == []
