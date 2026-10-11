"use strict";
const $ = (id) => document.getElementById(id);
const offline = Object.keys(window.DEMO_DATA || {}).length > 0;
let current = null,
  busy = false,
  importedPreview = false;
const pct = (x) => (100 * x).toFixed(1) + "%";
const signed = (x) => (x >= 0 ? "+" : "") + x.toFixed(2) + "%";
const set = (id, text) => {
  $(id).textContent = text;
};
function pending(value) {
  busy = value;
  $("simulate").disabled =
    value || (offline && $("preset").value === "imported");
  $("fork").disabled = value || !current || (offline && importedPreview);
  $("export").disabled = value || !current;
  $("reveal").disabled = value || !current || !current.result.demo_settlement;
  $("import-trigger").disabled = value;
  $("case").disabled = value;
  $("preset").disabled = value;
}
function element(tag, className, text) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text !== undefined) e.textContent = text;
  return e;
}
function fanChart(r) {
  const svg = $("fan"),
    ns = "http://www.w3.org/2000/svg";
  const width = Math.max(220, svg.clientWidth || 700);
  const left = 52,
    right = width - 16;
  const horizon = r.event_contract.horizon_days;
  svg.setAttribute("viewBox", `0 0 ${width} 230`);
  svg.setAttribute(
    "aria-label",
    `Simulated return fan over ${horizon} trading days`,
  );
  svg.replaceChildren();
  const scenario = [{ day: 0, p10: 0, p50: 0, p90: 0 }, ...r.scenario.fan];
  const baseline = [{ day: 0, p10: 0, p50: 0, p90: 0 }, ...r.baseline.fan];
  const vals = [...scenario, ...baseline].flatMap((p) => [p.p10, p.p90]);
  let lo = Math.min(...vals),
    hi = Math.max(...vals);
  const pad = (hi - lo) * 0.15 || 1;
  lo -= pad;
  hi += pad;
  const x = (d) => left + (d / horizon) * (right - left),
    y = (v) => 195 - ((v - lo) / (hi - lo)) * 170;
  const draw = (name, attrs, text) => {
    const e = document.createElementNS(ns, name);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (text !== undefined) e.textContent = text;
    svg.append(e);
  };
  for (let i = 0; i < 5; i++) {
    const v = lo + ((hi - lo) * i) / 4;
    draw("line", {
      x1: left,
      x2: right,
      y1: y(v),
      y2: y(v),
      stroke: "#28343d",
    });
    draw("text", { x: 0, y: y(v) + 3 }, signed(v));
  }
  for (const d of [0, ...r.scenario.fan.map((p) => p.day)])
    draw(
      "text",
      { x: x(d) - 6, y: 220 },
      d === horizon ? `${horizon}d` : String(d),
    );
  draw("polygon", {
    points: [
      ...scenario.map((p) => `${x(p.day)},${y(p.p90)}`),
      ...scenario
        .slice()
        .reverse()
        .map((p) => `${x(p.day)},${y(p.p10)}`),
    ].join(" "),
    fill: "#c0ee8f22",
    stroke: "none",
  });
  draw("polyline", {
    points: baseline.map((p) => `${x(p.day)},${y(p.p50)}`).join(" "),
    fill: "none",
    stroke: "#80c6cf",
    "stroke-width": 1.5,
    "stroke-dasharray": "5 5",
  });
  draw("polyline", {
    points: scenario.map((p) => `${x(p.day)},${y(p.p50)}`).join(" "),
    fill: "none",
    stroke: "#c0ee8f",
    "stroke-width": 2.5,
  });
}
function comparisons(r) {
  const c = $("comparison");
  c.replaceChildren();
  for (const [name, p] of [
    [
      "Scenario / reactions",
      { up: r.scenario.p_up, down: r.scenario.p_down, flat: r.scenario.p_flat },
    ],
    [
      "Swarm / no reaction",
      { up: r.baseline.p_up, down: r.baseline.p_down, flat: r.baseline.p_flat },
    ],
    ["Price-only quant", r.quant.probabilities],
    [
      "Student-t / no personas",
      {
        up: r.simple_baseline.p_up,
        down: r.simple_baseline.p_down,
        flat: 1 - r.simple_baseline.p_up - r.simple_baseline.p_down,
      },
    ],
  ]) {
    const row = element("div", "compare-row"),
      bar = element("div", "bar");
    bar.setAttribute("role", "img");
    bar.setAttribute(
      "aria-label",
      `DOWN ${pct(p.down)}, FLAT ${pct(p.flat)}, UP ${pct(p.up)}`,
    );
    row.append(element("span", "", name));
    for (const k of ["down", "flat", "up"]) {
      const part = element("span", k);
      part.style.width = pct(p[k]);
      bar.append(part);
    }
    row.append(bar, element("strong", "", pct(p.up)));
    c.append(row);
  }
}
function render(response, imported = false) {
  const r = response.result;
  if (
    !r ||
    !r.scenario ||
    !r.baseline ||
    !r.quant ||
    !r.evidence_graph ||
    !r.falsification ||
    !r.sensitivity ||
    !r.run
  )
    throw new Error("Incomplete scenario bundle");
  const numeric = [
    r.scenario.p_up,
    r.scenario.return_pct.p50,
    r.scenario.return_pct.p10,
    r.scenario.return_pct.p90,
  ];
  if (!numeric.every(Number.isFinite))
    throw new Error("Invalid scenario numbers");
  const b = JSON.parse(response.bundle_json),
    req = b.request;
  if (
    !req ||
    !["earnings", "policy", "liquidity"].includes(req.case) ||
    ![
      req.sentiment,
      req.persistence,
      req.retail_weight,
      req.worlds,
      req.seed,
      r.event_contract?.horizon_days,
    ].every(Number.isFinite) ||
    !Array.isArray(r.scenario.fan) ||
    !Array.isArray(r.baseline.fan) ||
    !Array.isArray(r.sensitivity.variants) ||
    !r.falsification.checks?.length ||
    !r.evidence_graph.nodes?.length
  )
    throw new Error("Incomplete scenario metadata");
  current = response;
  importedPreview = imported;
  $("output").hidden = false;
  $("settlement").hidden = true;
  $("case").value = req.case;
  if (imported) $("preset").value = "imported";
  set("sentiment", Number(req.sentiment).toFixed(2));
  set("persistence", req.persistence + " days");
  set("retail", pct(req.retail_weight));
  set("run-scale", `${r.event_contract.horizon_days} days / ${req.worlds}`);
  set("seed", String(req.seed));
  set("name", r.name);
  set("data-kind", r.symbol === "SYNTHETIC" ? "SYNTHETIC" : "USER DATA");
  set("headline", r.evidence_graph.nodes[0].text);
  set("p-up", pct(r.scenario.p_up));
  set(
    "shift",
    (r.shift.p_up >= 0 ? "+" : "") +
      (r.shift.p_up * 100).toFixed(1) +
      " pts vs no reaction",
  );
  set("median", signed(r.scenario.return_pct.p50));
  set(
    "range",
    signed(r.scenario.return_pct.p10) +
      " to " +
      signed(r.scenario.return_pct.p90),
  );
  fanChart(r);
  comparisons(r);
  set(
    "fragility",
    r.sensitivity.variants.length
      ? "P(UP) ranges from " +
          pct(r.sensitivity.p_up_range[0]) +
          " to " +
          pct(r.sensitivity.p_up_range[1]) +
          " across the supplied assumption sweep."
      : "Sensitivity was not run for this receipt. Its fragility is unknown.",
  );
  $("sensitivity-note").hidden = !r.sensitivity.variants.length;
  $("sensitivity").replaceChildren();
  for (const v of r.sensitivity.variants) {
    const e = element("div", "sweep");
    e.append(element("span", "", v.name), element("strong", "", pct(v.p_up)));
    $("sensitivity").append(e);
  }
  const f = r.falsification.checks[0];
  set(
    "failure",
    f.reason +
      " Threshold: " +
      Number(f.threshold).toFixed(2) +
      " at the horizon close.",
  );
  $("reveal").hidden = !r.demo_settlement;
  const graph = element("div", "nodes");
  for (const n of r.evidence_graph.nodes) {
    const e = element(
      "div",
      "node " +
        (["assumption", "interpretation"].includes(n.kind)
          ? n.kind
          : "measurement"),
    );
    e.append(
      element("strong", "", n.id + " / " + n.kind.toUpperCase()),
      element("span", "", String(n.text)),
    );
    if (n.evidence_ids)
      e.append(
        element("small", "", "Supported by → " + n.evidence_ids.join(", ")),
      );
    graph.append(e);
  }
  $("graph").replaceChildren(graph);
  set("run-id", r.run.run_id);
  set("parent-id", b.parent ? "Fork of " + b.parent : "Root scenario");
  set(
    "message",
    imported
      ? "Imported scenario preview. Its claims remain unverified."
      : "Frozen scenario ready. Challenge it or reveal the synthetic outcome.",
  );
  $("message").className = "";
  set(
    "integrity",
    imported && offline
      ? "Unverified file preview. Verify its hash with run_bundle in the CLI before relying on this receipt."
      : "Local hashes detect edits; they do not prove pre-event publication.",
  );
  pending(false);
}
async function run(action = "simulate") {
  if (busy || (offline && $("preset").value === "imported")) return;
  pending(true);
  set("message", "Simulating paired worlds…");
  $("message").className = "";
  try {
    const key = $("case").value + ":" + $("preset").value;
    if (offline) {
      render(window.DEMO_DATA[key]);
      if (action === "fork")
        set(
          "message",
          "Opened the precomputed fork of this case's original thesis. Export its frozen receipt.",
        );
      return;
    }
    const replayImported = $("preset").value === "imported";
    const body = {
      action: replayImported ? "fork" : action,
      case: $("case").value,
      preset: replayImported ? "original" : $("preset").value,
    };
    if (body.action === "fork") body.run_id = current.result.run.run_id;
    const response = await fetch("/api/scenario", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok || data.error)
      throw new Error(data.error || "Scenario unavailable");
    render(data);
    if (replayImported) {
      importedPreview = true;
      $("preset").value = "imported";
      set(
        "message",
        "Replayed the imported assumptions on the same frozen history. A new child receipt is saved.",
      );
    }
  } catch (e) {
    set("message", e.message);
    $("message").className = "error";
    pending(false);
  }
}
$("simulate").addEventListener("click", () => run());
$("fork").addEventListener("click", () => run("fork"));
$("import-trigger").addEventListener("click", () => $("import").click());
$("case").addEventListener("change", () => {
  $("preset").value = "original";
  run();
});
$("preset").addEventListener("change", () => {
  if (busy) return;
  set(
    "message",
    "Assumption selected. Run or fork to apply it; results still show the loaded run.",
  );
  pending(false);
});
$("export").addEventListener("click", () => {
  if (!current) return;
  const url = URL.createObjectURL(
    new Blob([current.bundle_json], { type: "application/json" }),
  );
  const a = element("a");
  a.href = url;
  a.download = "tradefloor-" + current.result.run.run_id + ".json";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
$("reveal").addEventListener("click", () => {
  if (busy || !current?.result.demo_settlement) return;
  const s = current.result.demo_settlement;
  set(
    "settlement",
    "Synthetic outcome: " +
      s.outcome +
      ". Close: " +
      s.close.toFixed(2) +
      ". Multiclass Brier: " +
      s.scores.brier_multiclass.toFixed(3) +
      ". Thesis: " +
      s.falsification.status +
      ". This is a demonstration, not a performance benchmark.",
  );
  $("settlement").hidden = false;
});
$("import").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file || busy) return;
  pending(true);
  try {
    if (file.size > 2000000) throw new Error("Import limit is 2 MB");
    const raw = await file.text(),
      b = JSON.parse(raw);
    if (b.schema !== "tradefloor-run-v1" || b.kind !== "scenario")
      throw new Error("Select a scenario run bundle");
    if (offline) {
      render(
        {
          result: { ...b.result, run: { run_id: b.id, sha256: b.sha256 } },
          bundle_json: raw,
        },
        true,
      );
    } else {
      pending(true);
      const response = await fetch("/api/scenario", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "import", bundle_json: raw }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error);
      render(data, true);
    }
  } catch (err) {
    set("message", err.message);
    $("message").className = "error";
    pending(false);
  }
  e.target.value = "";
});
if (offline)
  set(
    "mode-note",
    "Standalone demo: seven precomputed assumption sets per event. Each fork preserves the original frozen history. Arbitrary assumptions are available in the local CLI/MCP lab.",
  );
if (typeof ResizeObserver !== "undefined") {
  new ResizeObserver(() => {
    if (current) fanChart(current.result);
  }).observe($("fan"));
}
run();
