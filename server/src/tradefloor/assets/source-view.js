(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.TradefloorSources = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const samples = [
    { title: "Fictional ACME / earnings excerpt", source: "Tradefloor fictional source fixture", rights: "MIT synthetic educational text", published_at: "2026-09-27T12:00:00+00:00", available_at: "2026-09-27T12:00:00+00:00", kind: "text", content: "FICTIONAL EXAMPLE. ACME reports stronger demand and higher operating margins. Management raises its outlook, while cautioning that inventory spending may reduce near-term cash flow. These statements are invented for interface testing, not real company data." },
    { title: "Fictional ACME / risk note", source: "Tradefloor fictional source fixture", rights: "MIT synthetic educational text", published_at: "2026-09-27T13:00:00+00:00", available_at: "2026-09-27T13:00:00+00:00", kind: "text", content: "FICTIONAL EXAMPLE. The earnings surprise may already be reflected in the price. Demand could normalize and margin gains may reverse. The research question is whether measured attention persists beyond the announcement. These are invented objections, not an empirical forecast." }
  ];
  const escape = s => String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const md = s => escape(s).replace(/([\\`*_[\]{}()!#])/g,"\\$1");
  function offlineReport(current) {
    const b = JSON.parse(current.bundle_json), r = b.result;
    const report = { title:"Tradefloor / " + r.name, receipt:b.id, note:(r.symbol==="SYNTHETIC"?"Frozen synthetic demonstration.":"Supplied receipt preview; authenticity is unverified.")+" Conditional models, no demonstrated trading edge. Source dates and rights are asserted; links do not establish causality. No settlement is included.",
      paragraphs:[{heading:"Research question",text:r.name},{heading:"Provenance",text:`Symbol: ${r.symbol}\nFrozen: ${r.as_of}\nReceipt: ${b.id}\nSHA-256: ${b.sha256}`},{heading:"Numerical assumptions",text:JSON.stringify(Object.fromEntries(["case","sentiment","persistence","retail_weight","worlds","seed"].map(k=>[k,b.request[k]])),null,2)},{heading:"Conditional baselines",text:JSON.stringify({scenario:{up:r.scenario.p_up,down:r.scenario.p_down,flat:r.scenario.p_flat},no_reaction:{up:r.baseline.p_up,down:r.baseline.p_down,flat:r.baseline.p_flat},quant:r.quant.probabilities},null,2)}],
      claims:r.evidence_graph.nodes.filter(n=>n.kind==="interpretation").map(n=>({role:"scenario interpretation",...n,flags:[]})), observations:[{role:"scenario",kind:"falsification",text:JSON.stringify(r.falsification,null,2)}],
      sources:r.evidence_graph.nodes.filter(n=>n.kind!=="interpretation").map(n=>({id:n.id,kind:n.kind,status:n.status,text:n.text,source:n.source||"Unspecified",available_at:n.available_at,rights:n.rights||"Not specified",url:null})) };
    return {report,...serialize(report)};
  }
  function serialize(report) {
    const markdown=["# " + md(report.title),"",md(report.note)], html=[`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>${escape(report.title)}</title><style>body{max-width:900px;margin:40px auto;padding:0 24px;font:15px/1.7 system-ui;color:#17222b}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.7 monospace}section{margin:24px 0;border-top:1px solid #ccc}blockquote{border-left:3px solid #bbb;padding-left:16px}@media print{body{margin:0;max-width:none}}</style><body><h1>${escape(report.title)}</h1><p>${escape(report.note)}</p>`];
    for(const p of report.paragraphs){markdown.push("","## "+md(p.heading),"",md(p.text));html.push(`<section><h2>${escape(p.heading)}</h2><pre>${escape(p.text)}</pre></section>`);}
    markdown.push("","## Claims and references");html.push("<section><h2>Claims and references</h2>");
    for(const c of report.claims){const refs=(c.evidence_ids||[]).map(id=>{const index=report.sources.findIndex(s=>s.id===id);return index<0?md(id)+" (missing)":`[${md(id)}](#source-${index+1})`;});markdown.push("",md(c.role+" / "+c.id+": "+c.text),md(c.status),refs.join(", "));html.push(`<h3>${escape(c.role+" / "+c.id)}</h3><p>${escape(c.text)}</p><p>${escape(c.status)}</p>`);for(const id of c.evidence_ids||[]){const index=report.sources.findIndex(s=>s.id===id);html.push(index<0?escape(id)+" (missing)":`<a href="#source-${index+1}">${escape(id)}</a> `);}}
    html.push("</section><section><h2>Unresolved observations</h2>");markdown.push("","## Unresolved observations");
    for(const o of report.observations){markdown.push("",md(o.role+" / "+o.kind+": "+o.text));html.push(`<h3>${escape(o.role+" / "+o.kind)}</h3><pre>${escape(o.text)}</pre>`);}
    html.push("</section><section><h2>Source appendix</h2>");markdown.push("","## Source appendix");
    report.sources.forEach((s,i)=>{markdown.push("",`<a id="source-${i+1}"></a>`,"### "+md(s.id),"",md(s.text),"",md(JSON.stringify({...s,text:undefined},null,2)));html.push(`<article id="source-${i+1}"><h3>${escape(s.id)}</h3><blockquote>${escape(s.text)}</blockquote><pre>${escape(JSON.stringify({...s,text:undefined},null,2))}</pre></article>`);});
    html.push("</section></body></html>");return {markdown:markdown.join("\n"),html:html.join("")};
  }
  return {samples,escape,offlineReport,serialize};
});
