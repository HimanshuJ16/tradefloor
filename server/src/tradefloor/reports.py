"""Deterministic cited reports from frozen receipts and recorded model outputs."""
import html
import json
import re
from urllib.parse import urlsplit

from . import desk, runs


def _md(value):
    return re.sub(r"([\\`*_[\]{}()!#])", r"\\\1", html.escape(str(value), quote=True))


def _link(source):
    try:
        u = urlsplit(source)
        return source if u.scheme == "https" and u.hostname and not u.username and not u.password and not u.query and not u.fragment else None
    except ValueError:
        return None


def report(run_id=None, session_id=None):
    session = desk.session("get", session_id) if session_id else None
    bundle = json.loads(session["plan"]["source_bundle_json"]) if session else runs.read(run_id)
    if bundle["kind"] != "scenario":
        raise ValueError("Select a scenario receipt or research session")
    result = bundle["result"]
    paragraphs = [
        {"heading": "Research question", "text": session["plan"]["question"] if session else result["name"]},
        {"heading": "Provenance", "text": f"Symbol: {result['symbol']}\nFrozen date: {result['as_of']}\nReceipt: {bundle['id']}\nSHA-256: {bundle['sha256']}\nParent: {bundle['parent'] or 'none'}\nData: {result['data_kind']}"},
        {"heading": "Numerical assumptions", "text": json.dumps({k: bundle["request"][k] for k in ("sentiment", "persistence", "retail_weight", "worlds", "seed")}, indent=2)},
        {"heading": "Conditional baselines", "text": json.dumps({"scenario": {"up": result["scenario"]["p_up"], "down": result["scenario"]["p_down"], "flat": result["scenario"]["p_flat"]}, "no_reaction": {"up": result["baseline"]["p_up"], "down": result["baseline"]["p_down"], "flat": result["baseline"]["p_flat"]}, "quant": result["quant"]["probabilities"]}, indent=2)},
    ]
    claims, observations = [], []
    if session:
        paragraphs.append({"heading": "Session status", "text": session["state"] + " / " + (session.get("trust") or "Recorded local session; references do not establish truth.")})
        for r in session["responses"]:
            if r.get("error"):
                paragraphs.append({"heading": r["role"] + " / failed", "text": r["error"]})
                continue
            paragraphs.append({"heading": r["role"] + " / " + r["profile"]["model"], "text": r["output"]["summary"] + ("\nABSTAINED" if r["output"].get("abstain") else "")})
            if r["audit"].get("forecast"):
                paragraphs.append({"heading": r["role"] + " / validated probability structure", "text": json.dumps(r["audit"]["forecast"]["probabilities"], indent=2)})
            if r["audit"].get("probability_error"):
                paragraphs.append({"heading": r["role"] + " / rejected probability adjustment", "text": r["audit"]["probability_error"]})
            if r["output"].get("adjustments"):
                paragraphs.append({"heading": r["role"] + " / supplied adjustments", "text": json.dumps(r["output"]["adjustments"], ensure_ascii=False, indent=2)})
            claims.extend({**c, "role": r["role"]} for c in r["audit"]["claims"])
            for name in ("assumptions", "objections", "resolutions"):
                observations.extend({"role": r["role"], "kind": name, "text": v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)} for v in r["output"].get(name, []))
        paragraphs.append({"heading": "Recorded forecast differences", "text": json.dumps(desk._disagreements(session["responses"]), indent=2)})
    else:
        claims = [{"id": n["id"], "role": "scenario interpretation", "text": n["text"], "evidence_ids": n.get("evidence_ids", []), "flags": [], "status": n["status"]} for n in result["evidence_graph"]["nodes"] if n["kind"] == "interpretation"]
        observations.append({"role": "scenario", "kind": "falsification", "text": json.dumps(result["falsification"], ensure_ascii=False)})
    sources = []
    for n in result["evidence_graph"]["nodes"]:
        if n["kind"] == "interpretation":
            continue
        anchor = n.get("anchor")
        sources.append({"id": n["id"], "kind": n["kind"], "status": n["status"], "text": n["text"], "source": n.get("source", "Unspecified"),
                        "url": _link(n.get("source", "")), "published_at": n.get("published_at"), "available_at": n.get("available_at"), "rights": n.get("rights", "Not specified"),
                        "document_sha256": n.get("document_sha256"), "original_document_sha256": n.get("original_document_sha256"),
                        "span": [anchor["start"], anchor["end"]] if anchor else None})
    note = "Research record, not investment advice or demonstrated trading edge. Source dates/rights are asserted. Audits check reference consistency, not truth, entailment or causality. Model summaries are unverified. No synthetic settlement is included. Review source redistribution rights before sharing."
    model = {"schema": "tradefloor-report-v1", "title": "Tradefloor / " + result["name"], "receipt": bundle["id"], "paragraphs": paragraphs, "claims": claims, "observations": observations, "sources": sources, "note": note}
    markdown = ["# " + _md(model["title"]), "", _md(note)]
    for p in paragraphs:
        markdown.extend(["", "## " + _md(p["heading"]), "", _md(p["text"])])
    markdown.extend(["", "## Claims and references"])
    for c in claims:
        refs = ", ".join("[" + _md(eid) + "](#source-" + str(next((i + 1 for i, s in enumerate(sources) if s["id"] == eid), 0)) + ")" for eid in c["evidence_ids"])
        markdown.extend(["", _md(c["role"] + " / " + c["id"] + ": " + c["text"]), "Status: " + _md(c["status"]) + ". References: " + (refs or "none"), *[_md(flag) for flag in c.get("flags", [])]])
    markdown.extend(["", "## Unresolved observations"])
    for o in observations:
        markdown.extend(["", _md(o["role"] + " / " + o["kind"] + ": " + o["text"])])
    markdown.extend(["", "## Source appendix"])
    for i, s in enumerate(sources, 1):
        markdown.extend(["", f'<a id="source-{i}"></a>', "### " + _md(s["id"] + " / " + s["kind"]), "", _md(s["text"]), "", "```text", json.dumps({k: v for k, v in s.items() if k != "text"}, ensure_ascii=False, indent=2), "```"])
    # HTML uses escaping for every supplied field; no model HTML/Markdown is executed.
    esc = lambda value: html.escape(str(value), quote=True)
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'"><title>' + esc(model["title"]) + '</title><style>body{max-width:900px;margin:40px auto;padding:0 24px;font:15px/1.7 system-ui;color:#17222b}h1,h2,h3{line-height:1.3}section{border-top:1px solid #ccd5dc;padding-top:16px;margin:24px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.6 monospace}a{color:#24516d}blockquote{border-left:3px solid #bac8cf;padding-left:16px;margin-left:0}@media print{body{margin:0;max-width:none}h2,h3{break-after:avoid}section{break-inside:auto}a{color:inherit}}</style><body><h1>' + esc(model["title"]) + '</h1><p>' + esc(note) + '</p><p>Use your browser’s Print → Save as PDF to preserve this report.</p>']
    for p in paragraphs:
        parts.append("<section><h2>" + esc(p["heading"]) + "</h2><pre>" + esc(p["text"]) + "</pre></section>")
    parts.append("<section><h2>Claims and references</h2>")
    for c in claims:
        refs = []
        for eid in c["evidence_ids"]:
            index = next((i + 1 for i, s in enumerate(sources) if s["id"] == eid), None)
            refs.append(f'<a href="#source-{index}">{esc(eid)}</a>' if index else esc(eid) + " (missing)")
        parts.append("<h3>" + esc(c["role"] + " / " + c["id"]) + "</h3><p>" + esc(c["text"]) + "</p><p>" + esc(c["status"]) + " / " + (", ".join(refs) or "No references") + "</p><pre>" + esc("\n".join(c.get("flags", []))) + "</pre>")
    parts.append("</section><section><h2>Unresolved observations</h2>")
    for o in observations:
        parts.append("<h3>" + esc(o["role"] + " / " + o["kind"]) + "</h3><pre>" + esc(o["text"]) + "</pre>")
    parts.append("</section><section><h2>Source appendix</h2>")
    for i, s in enumerate(sources, 1):
        parts.append(f'<article id="source-{i}"><h3>{esc(s["id"] + " / " + s["kind"])}</h3><blockquote>{esc(s["text"])}</blockquote><pre>' + esc(json.dumps({k: v for k, v in s.items() if k != "text"}, ensure_ascii=False, indent=2)) + "</pre>" + (f'<a href="{esc(s["url"])}" rel="noopener noreferrer">Open original source</a>' if s["url"] else "") + "</article>")
    parts.append("</section></body></html>")
    return {"report": model, "markdown": "\n".join(markdown), "html": "".join(parts)}
