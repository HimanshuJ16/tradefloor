"""Immutable local source documents, exact extracted-text spans and explicit evidence forks."""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import math
import os
import re
import socket
import ssl
import subprocess
import sys
import time
from collections import Counter
from html.parser import HTMLParser
from http.client import HTTPSConnection
from urllib.parse import urlsplit

from . import lab, research, runs, settings, timeline
from .evidence import stamp, text
from .storage import canonical, connect

MAX_BYTES = 5_000_000


class VisibleHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.pieces, self.hidden = [], []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg", "template", "form"}:
            self.hidden.append(tag)
        if not self.hidden and tag in {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "section", "article"}:
            self.pieces.append("\n")
        if not self.hidden and tag in {"td", "th"}:
            self.pieces.append("\t")

    def handle_endtag(self, tag):
        if tag in self.hidden:
            del self.hidden[self.hidden.index(tag):]
        if not self.hidden and tag in {"p", "div", "li", "tr", "h1", "h2", "h3"}:
            self.pieces.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.pieces.append(data)


def database():
    return settings.home() / "library.sqlite3"


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _get(identifier):
    if not isinstance(identifier, str) or not re.fullmatch(r"[a-f0-9]{64}", identifier):
        raise ValueError("Invalid document identity")
    with connect(database()) as db:
        row = db.execute("SELECT body FROM records WHERE id=?", (identifier,)).fetchone()
    if not row:
        raise ValueError("Document not found")
    doc = json.loads(row[0])
    if runs.digest({k: v for k, v in doc.items() if k != "sha256"}) != doc["sha256"] or _hash(doc["text"].encode()) != doc["text_sha256"] or _hash(base64.b64decode(doc["original_base64"], validate=True)) != doc["original_sha256"]:
        raise ValueError("Document integrity check failed")
    return doc


def _summary(doc):
    return {k: doc[k] for k in ("id", "title", "source", "kind", "rights", "published_at", "available_at", "retrieved_at", "original_sha256", "text_sha256", "sha256", "pages")}


def chunks(doc):
    out, start = [], 0
    while start < len(doc["text"]):
        stop = min(len(doc["text"]), start + 1600)
        if stop < len(doc["text"]):
            boundary = max(doc["text"].rfind("\n", start + 600, stop), doc["text"].rfind(" ", start + 600, stop))
            if boundary > start:
                stop = boundary + 1
        if doc["text"][start:stop].strip():
            out.append({"id": "D" + doc["id"][:16] + "-" + str(len(out) + 1), "document_id": doc["id"], "start": start, "end": stop, "text": doc["text"][start:stop]})
        start = stop
    return out


def ingest(body):
    if not isinstance(body, dict):
        raise ValueError("Document settings must be an object")
    kind = body.get("kind", "text")
    if kind not in {"text", "html", "pdf"}:
        raise ValueError("Import text, HTML or a text-based PDF")
    if body.get("file_base64") is not None:
        value = body["file_base64"]
        if not isinstance(value, str) or len(value) > 6_666_672:
            raise ValueError("Document exceeds 5 MB")
        try:
            raw = base64.b64decode(value, validate=True)
        except ValueError:
            raise ValueError("Invalid document encoding") from None
    else:
        raw = text(body.get("content"), "document content", MAX_BYTES).encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise ValueError("Document exceeds 5 MB")
    pages = None
    if kind == "pdf":
        if not raw.startswith(b"%PDF-"):
            raise ValueError("Expected a PDF file")
        try:
            process = subprocess.run([sys.executable, "-m", "tradefloor.library_pdf"], input=raw, capture_output=True, timeout=20,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            extracted = json.loads(process.stdout)
        except (subprocess.TimeoutExpired, ValueError):
            raise ValueError("PDF extraction timed out or failed; import verified text instead") from None
        if process.returncode or extracted.get("error"):
            raise ValueError(extracted.get("error", "PDF extraction failed"))
        content, pages = extracted["text"], extracted["pages"]
    else:
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeError:
            raise ValueError("Use UTF-8 text/HTML or a text-based PDF") from None
        if kind == "html":
            parser = VisibleHTML()
            parser.feed(content)
            content = "".join(parser.pieces)
    content = text(content.replace("\r\n", "\n").replace("\r", "\n"), "extracted text", 200_000)
    if "\x00" in content:
        raise ValueError("Document contains binary text")
    published = stamp(body["published_at"]).isoformat() if body.get("published_at") else None
    available = stamp(body["available_at"]).isoformat() if body.get("available_at") else None
    if published and available and stamp(available) < stamp(published):
        raise ValueError("Availability cannot precede publication")
    doc = {"schema": "tradefloor-document-v1", "title": text(body.get("title"), "title", 160),
           "source": text(body.get("source"), "source", 2000), "rights": text(body.get("rights"), "rights", 500),
           "kind": kind, "text": content, "pages": pages, "published_at": published, "available_at": available,
           "original_sha256": _hash(raw), "text_sha256": _hash(content.encode()),
           "availability_status": "source/user asserted; retrieval does not establish historical availability"}
    identifier = runs.digest(doc)
    doc.update(id=identifier, retrieved_at=research.now(), original_base64=base64.b64encode(raw).decode())
    doc["sha256"] = runs.digest(doc)
    with connect(database()) as db:
        existing = db.execute("SELECT body FROM records WHERE id=?", (identifier,)).fetchone()
        if existing:
            doc = json.loads(existing[0])
        else:
            count, size = db.execute("SELECT count(*),coalesce(sum(length(body)),0) FROM records").fetchone()
            if count >= 250 or size + len(canonical(doc)) > 100_000_000:
                raise ValueError("Library limit reached: 250 documents / 100 MB of stored records")
            db.execute("INSERT INTO records(id,body) VALUES (?,?)", (identifier, canonical(doc)))
    return {**_summary(doc), "chunks": chunks(doc), "duplicate": bool(existing), "note": doc["availability_status"]}


def _eligible(doc, cutoff):
    return bool(doc["published_at"] and doc["available_at"] and stamp(doc["published_at"]) <= stamp(cutoff) and stamp(doc["available_at"]) <= stamp(cutoff))


def search(query, cutoff=None):
    query = text(query, "query", 500)
    terms = list(dict.fromkeys(re.findall(r"\w+", query.casefold())))[:32]
    if not terms:
        raise ValueError("Search needs words or numbers")
    with connect(database()) as db:
        documents = [json.loads(row[0]) for row in db.execute("SELECT body FROM records")]
    corpus = []
    for doc in documents:
        _get(doc["id"])
        for chunk in chunks(doc):
            words = re.findall(r"\w+", (doc["title"] + " " + chunk["text"]).casefold())
            corpus.append((doc, chunk, Counter(words), len(words)))
    n, average = len(corpus), sum(row[3] for row in corpus) / max(1, len(corpus))
    frequencies = {term: sum(term in row[2] for row in corpus) for term in terms}
    hits = []
    for doc, chunk, counts, length in corpus:
        score = sum(math.log(1 + (n - frequencies[term] + .5) / (frequencies[term] + .5)) * (counts[term] * 2.2) / (counts[term] + 1.2 * (.25 + .75 * length / max(1, average))) for term in terms if counts[term])
        if score > 0:
            hits.append({**chunk, "title": doc["title"], "source": doc["source"], "rights": doc["rights"], "score": score,
                         "eligible": _eligible(doc, cutoff) if cutoff else None, "published_at": doc["published_at"], "available_at": doc["available_at"]})
    hits.sort(key=lambda h: (-h["score"], h["document_id"], h["start"]))
    return {"hits": hits[:50], "matching_chunks": len(hits), "method": "Local BM25 lexical ranking; relevance is not factual validation", "cutoff": cutoff}


def freeze(run_id, selections):
    if not isinstance(selections, list) or not 1 <= len(selections) <= 20:
        raise ValueError("Select 1..20 exact document passages")
    bundle = runs.read(run_id)
    if bundle["kind"] != "scenario":
        raise ValueError("Open a frozen scenario first")
    cutoff = bundle["result"]["as_of"] + "T23:59:59+00:00"
    evidence = list(bundle["inputs"]["evidence"])
    ids = {e["id"] for e in evidence}
    for selection in selections:
        doc = _get(selection["document_id"])
        if not _eligible(doc, cutoff):
            raise ValueError("Selected source has unknown or later availability; use a compatible scenario cutoff")
        chunk = next((c for c in chunks(doc) if c["id"] == selection.get("chunk_id")), None)
        if not chunk:
            raise ValueError("Select a known, exact passage")
        if chunk["id"] in ids:
            continue
        evidence.append({"id": chunk["id"], "kind": "source", "text": chunk["text"], "source": doc["source"],
                         "source_family": "document:" + doc["original_sha256"], "rights": doc["rights"],
                         "published_at": doc["published_at"], "available_at": doc["available_at"],
                         "document_sha256": doc["text_sha256"], "original_document_sha256": doc["original_sha256"],
                         "library_document_id": doc["id"], "anchor": {"document_text": doc["text"], "start": chunk["start"], "end": chunk["end"]},
                         "availability_status": doc["availability_status"]})
        ids.add(chunk["id"])
    if len(evidence) == len(bundle["inputs"]["evidence"]):
        raise ValueError("These passages are already in the loaded receipt")
    return lab.simulate(**{**bundle["request"], "evidence": evidence, "claims": bundle["inputs"].get("claims"),
                          "price_snapshot": bundle["inputs"]["prices"], "synthetic_outcome": bundle["inputs"].get("synthetic_outcome"), "parent_run_id": run_id})


def documents(action="list", document_id=None, body=None):
    body = body or {}
    if action == "import":
        return ingest(body)
    if action == "search":
        return search(body.get("query"), body.get("cutoff"))
    if action == "freeze":
        result = freeze(body.get("run_id"), body.get("selections"))
        return {"result": result, "bundle_json": canonical(runs.read(result["run"]["run_id"]))}
    if action == "get":
        doc = _get(document_id)
        return {**_summary(doc), "text": doc["text"], "chunks": chunks(doc), "note": doc["availability_status"]}
    if action == "list":
        with connect(database()) as db:
            ids = [row[0] for row in db.execute("SELECT id FROM records ORDER BY seq DESC")]
        return {"documents": [_summary(_get(identifier)) for identifier in ids]}
    raise ValueError("Unknown library action")


def public_url(value, resolve=False):
    u = urlsplit(text(value, "source URL", 2000))
    if u.scheme != "https" or not u.hostname or u.username or u.password or u.query or u.fragment or u.port not in (None, 443):
        raise ValueError("Use a public HTTPS document URL without credentials, query or fragment, on port 443")
    hostname = u.hostname.encode("idna").decode()
    try:
        addresses = [str(ipaddress.ip_address(hostname))]
    except ValueError:
        addresses = []
    if resolve:
        try:
            addresses = list(dict.fromkeys(row[4][0] for row in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)))
        except OSError:
            raise ValueError("Source DNS lookup failed") from None
    if not addresses and resolve or any(not ipaddress.ip_address(a).is_global for a in addresses) or hostname in {"localhost", "localhost.localdomain"}:
        raise ValueError("Source requests require public Internet addresses")
    return u, hostname, addresses


def _download(url):
    u, hostname, addresses = public_url(url, resolve=True)
    context = ssl.create_default_context()

    class PinnedHTTPS(HTTPSConnection):
        def connect(self):
            # Connect to the address we validated; retain the original TLS hostname.
            sock = socket.create_connection((addresses[0], 443), timeout=12)
            try:
                self.sock = context.wrap_socket(sock, server_hostname=hostname)
            except Exception:
                sock.close()
                raise

    agent = "Tradefloor/0.5 (local research capture)"
    if hostname in {"www.sec.gov", "data.sec.gov"}:
        from .datahub import source_credential
        agent = os.environ.get("TRADEFLOOR_SEC_USER_AGENT") or source_credential("sec")
        if "@" not in agent:
            raise ValueError("Configure SEC application/contact in Data hub before fetching a filing")
    connection = PinnedHTTPS(hostname, timeout=12, context=context)
    try:
        deadline = time.monotonic() + 20
        connection.request("GET", u.path or "/", headers={"User-Agent": agent, "Accept-Encoding": "identity"})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError("Source returned HTTP " + str(response.status) + "; redirects are not followed")
        content_type = response.getheader("Content-Type", "").split(";")[0].lower()
        if content_type not in {"text/html", "application/xhtml+xml", "text/plain", "application/pdf"}:
            raise ValueError("Source must return HTML, plain text or PDF")
        if response.getheader("Content-Encoding", "identity") != "identity":
            raise ValueError("Source returned unsupported compression")
        pieces, size = [], 0
        while True:
            block = response.read(65536)
            if not block:
                break
            size += len(block)
            if size > MAX_BYTES or time.monotonic() > deadline:
                raise ValueError("Source exceeded the 5 MB / time limit")
            pieces.append(block)
        return b"".join(pieces), "pdf" if content_type == "application/pdf" else "text" if content_type == "text/plain" else "html"
    except (OSError, TimeoutError):
        raise ValueError("Source request failed; check availability and connectivity") from None
    finally:
        connection.close()


def discovery(action="sec", body=None):
    body = body or {}
    if action == "capture":
        raw, kind = _download(body.get("url"))
        return ingest({**body, "source": body["url"], "kind": kind, "file_base64": base64.b64encode(raw).decode()})
    if action != "sec":
        raise ValueError("Discover SEC filings or explicitly capture a public document URL")
    cik = text(body.get("cik"), "CIK", 10)
    result = timeline.fetch("sec", cik)
    rows = []
    for r in result["records"]:
        value = r["value"]
        if body.get("form") and value["form"] != body["form"]:
            continue
        accession, primary = value["accession"], value["primary_document"]
        if not re.fullmatch(r"[\d-]+", accession) or not re.fullmatch(r"[\w.-]+", primary):
            continue
        rows.append({"title": value["company"] + " / " + value["form"] + " / " + value["filing_date"],
                     "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{primary}",
                     "published_at": r["published_at"], "available_at": r["available_at"], "form": value["form"],
                     "note": "SEC acceptance metadata; dissemination latency and historical document versions unverified"})
    return {"sources": rows[:30], "scope": result["scope"], "note": "Discovery fetches metadata only. Select a filing and explicitly capture its document."}
