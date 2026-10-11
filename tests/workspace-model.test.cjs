const test = require("node:test");
const assert = require("node:assert/strict");
const view = require("../server/src/tradefloor/assets/workspace-model.js");
const result = {
  event_contract: { reference_price: 200, flat_band: Math.log(1.02) },
  scenario: { p_up: .55, p_down: .25, fan: [{ day: 5, p10: -10, p50: 2, p90: 12 }] },
  baseline: { p_up: .35, fan: [{ day: 5, p10: -8, p50: 1, p90: 9 }] },
  evidence_graph: { nodes: [{ kind: "assumption", status: "active" }, { kind: "source", status: "retracted" }, { kind: "interpretation", status: "review required" }] }
};
test("price view uses percentage returns and the frozen reference, not log returns", () => {
  const prices = view.series(result, "price");
  assert.equal(prices.scenario[0].p50, 200);
  assert.equal(prices.scenario[1].p10, 180);
  assert.equal(prices.scenario[1].p50, 204);
  assert.equal(view.series(result).scenario[1].p50, 2);
  assert.equal(result.scenario.fan.length, 1);
});
test("scrubber selects an actual saved observation without interpolating uncertainty", () => {
  const rows = [{ day: 0 }, { day: 5 }, { day: 10 }, { day: 21 }];
  assert.equal(view.nearest(rows, 13).day, 10);
  assert.equal(view.nearest(rows, 30).day, 21);
  assert.equal(view.nearest(rows, -4).day, 0);
});
test("summary uses probability points and distinguishes review flags from sources", () => {
  const s = view.summary(result);
  assert.equal(s.direction, "UP");
  assert.ok(Math.abs(s.shiftPoints - 20) < 1e-10);
  assert.equal(s.assumptions, 1);
  assert.equal(s.sources, 1);
  assert.equal(s.review, 2);
  assert.ok(Math.abs(s.flatUpper - 2) < 1e-10);
  assert.ok(Math.abs(s.flatLower - (100 / 1.02 - 100)) < 1e-10);
});
test("balanced probabilities are explicitly sideways rather than a buy or sell signal", () => {
  assert.equal(view.summary({ ...result, scenario: { ...result.scenario, p_up: .4, p_down: .4 } }).direction, "SIDEWAYS");
});
