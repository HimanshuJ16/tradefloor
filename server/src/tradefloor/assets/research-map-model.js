/* Recorded relationships only: no inferred attention, causality or model reasoning. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.TradefloorMapModel = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const key = (type, ...parts) => type + ":" + JSON.stringify(parts);
  const groups = { thesis: "context", branch: "context", evidence: "sources", assumption: "sources", agent: "agents", tool: "agents", claim: "findings", objection: "findings", test: "findings", forecast: "forecasts" };
  function build({ session = null, current = null, cursor = null } = {}) {
    let bundle;
    try { bundle = JSON.parse(session?.plan?.source_bundle_json || current?.bundle_json || "null"); } catch { return { nodes: [], edges: [], events: [], cursor: 0 }; }
    if (!bundle) return { nodes: [], edges: [], events: [], cursor: 0 };
    const result = bundle.result, context = session?.plan?.context;
    const events = session?.events || [], step = cursor === null ? events.length : Math.max(0, Math.min(events.length, Number(cursor) || 0));
    const visibleEvents = events.slice(0, step), latest = step === events.length;
    const nodes = [], edges = [], byId = new Map(), edgeIds = new Set();
    const add = n => { if (!byId.has(n.id)) { n.group = groups[n.type]; nodes.push(n); byId.set(n.id, n); } return n.id; };
    const link = (from, to, relation, warning = false) => { const id = key("edge", from, to, relation); if (byId.has(from) && byId.has(to) && !edgeIds.has(id)) { edgeIds.add(id); edges.push({ from, to, relation, warning }); } };
    const hub = add({ id: "thesis", type: "thesis", label: context?.symbol || result.symbol, text: session?.plan?.question || result.name, status: session ? latest ? session.state : "replay" : "frozen scenario", detail: { receipt: bundle.id, cutoff: context?.cutoff || result.as_of, imported: !!session?.imported, trust: session?.trust || "Local receipt; integrity does not establish accuracy." } });
    const eligible = context ? new Set(context.inspect_evidence.map(e => e.id)) : null;
    for (const n of result.evidence_graph.nodes) {
      const interpretation = n.kind === "interpretation", sent = !eligible || eligible.has(n.id);
      add({ id: key("source", n.id), evidenceId: interpretation ? null : n.id, type: interpretation ? "claim" : n.kind === "assumption" ? "assumption" : "evidence", label: n.id, text: n.text, status: !interpretation && !sent ? "excluded from model context" : n.status || "active", detail: n, withdrawable: !interpretation && n.status !== "retracted", warning: (n.status || "active") !== "active" || (!interpretation && !sent) });
      if (!interpretation) link(hub, key("source", n.id), sent ? "frozen input" : "excluded input", !sent);
    }
    for (const e of result.evidence_graph.edges) link(key("source", e.from), key("source", e.to), e.kind, e.kind === "contradicts");
    const baselines = context?.baseline_forecasts || { quant: result.quant.probabilities, scenario: { up: result.scenario.p_up, down: result.scenario.p_down, flat: result.scenario.p_flat }, no_reaction: { up: result.baseline.p_up, down: result.baseline.p_down, flat: result.baseline.p_flat } };
    for (const [name, probabilities] of Object.entries(baselines)) {
      const id = add({ id: key("baseline", name), type: "forecast", label: name.replaceAll("_", " "), text: "Frozen numerical baseline", status: "conditional model", detail: { probabilities } });
      link(hub, id, "numerical baseline");
    }
    if (bundle.parent) {
      const id = add({ id: key("branch", bundle.parent), type: "branch", label: "Parent receipt", text: bundle.parent, status: "lineage", detail: { receipt: bundle.parent } });
      link(id, hub, "forked from");
    }
    const responses = (session?.responses || []).filter(r => latest || visibleEvents.some(e => (e.kind === "response" || e.kind === "role_failed") && e.body.role === r.role));
    for (const route of session?.plan?.routes || []) {
      const role = route.role, row = responses.find(r => r.role === role), activity = visibleEvents.filter(e => e.body.role === role);
      let status = row?.error ? "failed" : row?.output ? row.output.abstain ? "abstained" : "completed" : activity.length ? "working" : "queued";
      if (latest && ["failed", "cancelled"].includes(session.state) && !row) status = session.state === "cancelled" ? "cancelled" : "interrupted";
      if (session.state === "preview") status = "preview; no calls";
      const agent = add({ id: key("agent", role), type: "agent", label: role, text: route.profile.name + " / " + route.profile.model, status, warning: ["failed", "interrupted", "cancelled"].includes(status) || !!row?.audit?.issues?.length || !!row?.audit?.probability_error, detail: { connection: route.profile.name, model: route.profile.model, protocol: route.profile.protocol, audit_issues: row?.audit?.issues || [], probability_error: row?.audit?.probability_error || null, activity: activity.map(e => ({ kind: e.kind, at: e.at, ...e.body })) } });
      link(hub, agent, "receives frozen context");
      for (const [i, e] of visibleEvents.entries()) if (e.body.role === role && e.kind === "tool_result") {
        const tool = add({ id: key("tool", role, i), type: "tool", label: e.body.tools?.join(" + ") || "Tool receipt", text: "Read-only frozen-context tool", status: "recorded", detail: e.body });
        link(agent, tool, "requested tool");
      }
      if (!row?.output) continue;
      const forecast = row.audit?.forecast;
      if (forecast && !row.output.abstain) {
        const id = add({ id: key("forecast", role), type: "forecast", label: role + " forecast", text: row.output.summary, status: forecast.direction, detail: { probabilities: forecast.probabilities, adjustments: row.output.adjustments, note: row.audit.note } });
        link(agent, id, "produced forecast");
        for (const adjustment of row.output.adjustments || []) for (const eid of adjustment.evidence_ids || []) link(key("source", eid), id, "cited for adjustment");
      }
      for (const [i, claim] of (row.audit?.claims || []).entries()) {
        const id = add({ id: key("claim", role, i), type: "claim", label: role + " / " + claim.id, text: claim.text, status: claim.status, warning: !!claim.flags?.length, detail: { ...claim, supplied_references: row.output.claims?.[i], audit_note: row.audit.note } });
        link(agent, id, "produced claim");
        for (const eid of claim.evidence_ids || []) {
          const source = key("source", eid);
          if (!byId.has(source)) add({ id: source, type: "evidence", label: eid, text: "Reference absent from the frozen evidence", status: "missing reference", warning: true, detail: {} });
          link(source, id, "cited reference", claim.flags?.length > 0 || (eligible && !eligible.has(eid)));
        }
      }
      for (const type of ["objections", "resolutions"]) for (const [i, value] of (row.output[type] || []).entries()) {
        const id = add({ id: key(type, role, i), type: type === "objections" ? "objection" : "test", label: role + (type === "objections" ? " objection" : " proposed test"), text: typeof value === "string" ? value : value.question, status: "model proposal", detail: typeof value === "string" ? { text: value } : value });
        link(agent, id, "proposed");
      }
    }
    // Recompute comparisons from the visible audited forecasts, never trust archive comparisons.
    const forecasts = nodes.filter(n => n.id.startsWith("forecast:"));
    for (let i = 0; i < forecasts.length; i++) for (const other of forecasts.slice(i + 1)) {
      const n = forecasts[i], gap = Math.max(...["up", "down", "flat"].map(k => Math.abs(n.detail.probabilities[k] - other.detail.probabilities[k])));
      if (n.status !== other.status || gap > 1e-9) link(n.id, other.id, "forecast disagreement; " + (gap * 100).toFixed(1) + " point gap", true);
    }
    return { nodes, edges, events, cursor: step, receipt: bundle.id, sessionId: session?.id, imported: !!session?.imported, source: session ? "session" : "scenario", latest };
  }
  function impact(graph, id) {
    const affected = new Set(), pending = [id];
    const relationships = new Set(["supports", "depends-on", "contradicts", "cited reference", "cited for adjustment"]);
    while (pending.length) {
      const from = pending.shift();
      for (const e of graph.edges) if (e.from === from && relationships.has(e.relation) && e.to !== id && !affected.has(e.to)) { affected.add(e.to); pending.push(e.to); }
    }
    return graph.nodes.filter(n => affected.has(n.id));
  }
  function filter(graph, { query = "", group = "all", focus = null, warnings = false } = {}) {
    const q = query.trim().toLowerCase(), neighbors = new Set([focus]);
    for (const e of graph.edges) if (e.from === focus || e.to === focus) { neighbors.add(e.from); neighbors.add(e.to); }
    const ids = new Set(graph.nodes.filter(n => (!focus || neighbors.has(n.id)) && (group === "all" || n.group === group) && (!warnings || n.warning || graph.edges.some(e => e.warning && (e.from === n.id || e.to === n.id))) && (!q || (n.label + " " + n.text + " " + n.status).toLowerCase().includes(q))).map(n => n.id));
    return { nodes: graph.nodes.filter(n => ids.has(n.id)), edges: graph.edges.filter(e => ids.has(e.from) && ids.has(e.to)) };
  }
  function positions(nodes) {
    const centers = { thesis: [485, 285], evidence: [190, 260], assumption: [240, 430], agent: [600, 145], tool: [410, 100], claim: [795, 285], forecast: [540, 490], objection: [810, 440], test: [830, 545], branch: [165, 85] }, counts = {};
    return nodes.map(n => {
      const i = counts[n.type] || 0; counts[n.type] = i + 1;
      if (n.type === "agent") return { ...n, x: 590 + (i % 2) * 145, y: 80 + Math.floor(i / 2) * 58 };
      if (n.type === "tool") return { ...n, x: 400, y: 70 + i * 38 };
      const [x, y] = centers[n.type], radius = n.type === "thesis" ? 0 : 45 * Math.sqrt(i), angle = i * 2.399963;
      return { ...n, x: x + Math.cos(angle) * radius, y: y + Math.sin(angle) * radius * .72 };
    });
  }
  return { build, impact, filter, positions, key };
});
