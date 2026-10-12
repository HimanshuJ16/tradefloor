const test = require("node:test"), assert = require("node:assert/strict");
const M = require("../server/src/tradefloor/assets/research-map-model.js");
const fixture = require("./fixtures/scenario.json");
function session() {
  const bundle = JSON.parse(fixture.bundle_json), graph = bundle.result.evidence_graph;
  const probabilities = { up: .6, down: .2, flat: .2 };
  const response = { role: "bull", output: { summary: "Inspectable claim", claims: [{ id: "C1", evidence_ids: ["E1"] }], adjustments: [{ class: "up", delta: .01, evidence_ids: ["E1"] }], objections: ["May be priced in"], resolutions: [{ question: "What would resolve it?", test: "Measure decay" }] }, audit: { claims: [{ id: "C1", text: "The event is an assumption", evidence_ids: ["E1"], flags: [], status: "references checked" }], forecast: { direction: "UP", probabilities }, note: "Not verified truth" } };
  const routes = ["bull", "bear"].map(role => ({ role, profile: { name: role, model: "mock", protocol: "openai" } }));
  const other = structuredClone(response); other.role = "bear"; other.audit.forecast.direction = "DOWN"; other.audit.forecast.probabilities = { up: .2, down: .6, flat: .2 };
  return { id: "session", state: "completed", plan: { source_bundle_json: fixture.bundle_json, question: "What changes this thesis?", context: { symbol: "SYNTHETIC", inspect_evidence: graph.nodes.filter(n => n.kind !== "interpretation"), baseline_forecasts: { quant: bundle.result.quant.probabilities } }, routes }, responses: [response, other], events: [{ kind: "model_call", body: { role: "bull" } }, { kind: "response", body: { role: "bull" } }, { kind: "role_failed", body: { role: "bear" } }] };
}
test("replay never reveals completed claims or forecasts before their response checkpoint", () => {
  const s = session();
  const beginning = M.build({ session: s, cursor: 0 });
  assert.equal(beginning.nodes.find(n => n.label === "bull").status, "queued");
  const calling = M.build({ session: s, cursor: 1 });
  assert.equal(calling.nodes.find(n => n.label === "bull").status, "working");
  assert.ok(!calling.nodes.some(n => n.id.startsWith("forecast:")));
  const answer = M.build({ session: s, cursor: 2 });
  assert.equal(answer.nodes.filter(n => n.id.startsWith("forecast:")).length, 1);
  assert.ok(!answer.edges.some(e => e.relation.startsWith("forecast disagreement")));
});
test("explicit references trace withdrawal impact without inferring every claim changes a forecast", () => {
  const graph = M.build({ session: session() });
  const affected = M.impact(graph, M.key("source", "E1"));
  assert.ok(affected.some(n => n.id === M.key("claim", "bull", 0)));
  assert.ok(affected.some(n => n.id === M.key("forecast", "bull")));
  assert.ok(!affected.some(n => n.type === "agent" || n.id.startsWith("baseline:")));
  assert.ok(graph.edges.some(e => e.relation.startsWith("forecast disagreement")));
});
test("dependency impact traverses chains and terminates on cycles", () => {
  const graph = { nodes: ["E", "C1", "C2"].map(id => ({ id })), edges: [{ from: "E", to: "C1", relation: "supports" }, { from: "C1", to: "C2", relation: "depends-on" }, { from: "C2", to: "C1", relation: "depends-on" }] };
  assert.deepEqual(M.impact(graph, "E").map(n => n.id), ["C1", "C2"]);
});
test("imported comparisons are recomputed from visible audited forecasts", () => {
  const s = session(); s.imported = true; s.disagreements = [{ left: "invented", right: "invented" }];
  const graph = M.build({ session: s });
  assert.equal(graph.imported, true);
  assert.equal(graph.edges.filter(e => e.relation.startsWith("forecast disagreement")).length, 1);
  assert.ok(!graph.nodes.some(n => n.label === "invented"));
});
test("missing evidence references and excluded inputs are marked for review", () => {
  const s = session(); s.responses[0].audit.claims[0].evidence_ids = ["missing"];
  s.plan.context.inspect_evidence = [];
  const g = M.build({ session: s });
  assert.equal(g.nodes.find(n => n.label === "missing").status, "missing reference");
  assert.equal(g.nodes.find(n => n.label === "E1").status, "excluded from model context");
  assert.ok(g.edges.find(e => e.from === M.key("source", "missing")).warning);
});
test("filters and focus retain only explicit connections and layout stays deterministic", () => {
  const graph = M.build({ session: session() });
  const filtered = M.filter(graph, { group: "agents", query: "bull" });
  assert.equal(filtered.nodes.length, 1);
  assert.equal(filtered.nodes[0].label, "bull");
  const focused = M.filter(graph, { focus: M.key("claim", "bull", 0) });
  assert.ok(focused.nodes.some(n => n.label === "E1"));
  assert.ok(!focused.nodes.some(n => n.label === "bear"));
  assert.deepEqual(M.positions(graph.nodes), M.positions(graph.nodes));
  assert.equal(new Set(graph.nodes.map(n => n.id)).size, graph.nodes.length);
});
test("cancelled sessions preserve completed output while marking unfinished roles", () => {
  const s = session(); s.state = "cancelled"; s.responses.pop();
  const g = M.build({ session: s });
  assert.equal(g.nodes.find(n => n.label === "bull").status, "completed");
  assert.equal(g.nodes.find(n => n.label === "bear").status, "cancelled");
});
test("a completed response with a rejected probability adjustment remains visible in review filters", () => {
  const s = session(); s.responses[0].audit.forecast = null;
  s.responses[0].audit.probability_error = "Adjustments exceed the allowed evidence-supported bound";
  const graph = M.build({ session: s });
  const flags = M.filter(graph, { warnings: true });
  assert.ok(flags.nodes.some(n => n.id === M.key("agent", "bull") && n.warning));
  assert.ok(!graph.nodes.some(n => n.id === M.key("forecast", "bull")));
});
test("scenario map preserves parent lineage and does not require a provider", () => {
  const b = JSON.parse(fixture.bundle_json); b.parent = "parent-receipt";
  const graph = M.build({ current: { bundle_json: JSON.stringify(b) } });
  assert.ok(graph.nodes.some(n => n.type === "branch" && n.text === "parent-receipt"));
  assert.ok(!graph.nodes.some(n => n.type === "agent"));
  assert.equal(graph.events.length, 0);
});
