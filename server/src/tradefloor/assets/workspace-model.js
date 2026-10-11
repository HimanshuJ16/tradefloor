/* Pure presentation calculations shared by the browser and regression tests. */
"use strict";
((root) => {
  function series(result, mode = "return") {
    const anchor = result.event_contract.reference_price;
    const convert = value => mode === "price" ? anchor * (1 + value / 100) : value;
    const build = model => [{ day: 0, p10: 0, p50: 0, p90: 0 }, ...model.fan].map(row => ({
      day: row.day, p10: convert(row.p10), p50: convert(row.p50), p90: convert(row.p90)
    }));
    return { scenario: build(result.scenario), baseline: build(result.baseline) };
  }
  function nearest(rows, day) {
    return rows.reduce((best, row) => Math.abs(row.day - day) < Math.abs(best.day - day) ? row : best, rows[0]);
  }
  function summary(result) {
    const s = result.scenario;
    const spread = s.p_up - s.p_down;
    const direction = spread >= .08 ? "UP" : spread <= -.08 ? "DOWN" : "SIDEWAYS";
    const nodes = result.evidence_graph.nodes;
    return {
      direction,
      shiftPoints: 100 * (s.p_up - result.baseline.p_up),
      spreadPoints: 100 * spread,
      assumptions: nodes.filter(n => n.kind === "assumption").length,
      sources: nodes.filter(n => ["source", "measurement"].includes(n.kind)).length,
      review: nodes.filter(n => n.status && n.status !== "active").length,
      flatLower: 100 * Math.expm1(-result.event_contract.flat_band),
      flatUpper: 100 * Math.expm1(result.event_contract.flat_band)
    };
  }
  const api = { series, nearest, summary };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.TradefloorView = api;
})(typeof window !== "undefined" ? window : {});
