"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const offline = Object.keys(window.DEMO_DATA || {}).length > 0;
  const state = { current: null, project: null, branches: new Map(), busy: false, job: null, importing: "run", preview: false, chartMode: "return", chartIndex: null };
  const pct = (n) => (100 * n).toFixed(1) + "%";
  const signed = (n) => (n >= 0 ? "+" : "") + n.toFixed(2) + "%";
  const el = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
  const set = (id, value) => { $(id).textContent = value; };
  function status(message, error = false) { set("status", message); $("status").className = error ? "error" : ""; }
  function remember(key, value) { try { localStorage.setItem(key, value); } catch (_) { /* storage can be disabled */ } }
  function recalled(key) { try { return localStorage.getItem(key); } catch (_) { return null; } }
  function busy(value) {
    state.busy = value;
    $("assumptions").disabled = value || offline;
    for (const button of document.querySelectorAll("[data-case]")) button.disabled = value;
    for (const id of ["run", "fork", "case", "preset", "project-select", "save-project", "open-run", "open-project", "challenge", "investigate", "arena", "fetch-source"]) $(id).disabled = value;
    $("fork").disabled = value || !state.current || state.preview;
    $("export-run").disabled = value || !state.current;
    $("reveal").disabled = value || !state.current?.result.demo_settlement;
    $("challenge").disabled = value || !state.current || state.preview;
    $("investigate").disabled = value || !state.current || offline || state.preview;
    $("arena").disabled = value || !state.current || offline || state.preview;
    $("fetch-source").disabled = value || offline;
    $("run").disabled = value || (offline && $("preset").value === "custom");
  }
  async function api(action, args = {}) {
    if (offline) throw new Error("This action requires the local Tradefloor workspace. The standalone demo uses frozen examples.");
    const r = await fetch("/api/workspace", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action, arguments: args }) });
    const data = await r.json();
    if (!r.ok || data.error) throw new Error(data.error || "Workspace request failed");
    return data;
  }
  async function guarded(fn) {
    if (state.busy) return;
    busy(true);
    try { await fn(); } catch (e) { status(e.message, true); } finally { if (!state.job) busy(false); }
  }
  function tab(name) {
    for (const button of document.querySelectorAll("[data-tab]")) {
      const active = button.dataset.tab === name;
      button.classList.toggle("active", active);
      if (active) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
      $("view-" + button.dataset.tab).hidden = !active;
    }
    if (name === "thesis" && state.current) fan(state.current.result);
  }
  for (const button of document.querySelectorAll("[data-tab]")) button.addEventListener("click", () => tab(button.dataset.tab));
  function jsonResult(id, data) { $(id).replaceChildren(el("pre", JSON.stringify(data, null, 2))); }
  function table(id, headers, rows) {
    const wrap = el("div", undefined, "table-wrap"), t = el("table"), head = el("thead"), tr = el("tr");
    for (const h of headers) tr.append(el("th", h));
    head.append(tr); t.append(head);
    const body = el("tbody");
    for (const row of rows) { const line = el("tr"); for (const cell of row) line.append(el("td", String(cell))); body.append(line); }
    t.append(body); wrap.append(t); $(id).replaceChildren(wrap);
  }
  function validate(response) {
    const b = JSON.parse(response.bundle_json), r = response.result;
    if (b.schema !== "tradefloor-run-v1" || b.kind !== "scenario" || !/^[a-f0-9]{32}$/.test(b.id) || !r || r.run?.run_id !== b.id) throw new Error("Select a valid scenario receipt");
    const req = b.request;
    if (!Number.isFinite(r.event_contract?.reference_price) || r.event_contract.reference_price <= 0 || !Number.isFinite(r.event_contract.flat_band) || r.event_contract.flat_band < 0) throw new Error("Invalid price anchor or event band");
    if (!["earnings", "policy", "liquidity"].includes(req?.case) || ![req.sentiment, req.persistence, req.retail_weight, req.seed, req.worlds, r.event_contract?.horizon_days].every(Number.isFinite)) throw new Error("Invalid scenario metadata");
    for (const x of [r.scenario, r.baseline]) {
      if (!x || ![x.p_up, x.p_down, x.p_flat].every(n => Number.isFinite(n) && n >= 0 && n <= 1) || Math.abs(x.p_up + x.p_down + x.p_flat - 1) > .002) throw new Error("Invalid scenario probabilities");
      for (const q of [x.return_pct, x.price, ...(x.fan || [])]) if (!q || ![q.p10, q.p50, q.p90].every(Number.isFinite) || q.p10 > q.p50 || q.p50 > q.p90) throw new Error("Invalid scenario quantiles");
      if (!Array.isArray(x.fan) || !x.fan.length || x.fan.length > 252 || !x.fan.every(p => Number.isFinite(p.day) && p.day > 0 && p.day <= r.event_contract.horizon_days)) throw new Error("Invalid return fan");
    }
    if (!r.quant?.probabilities || !r.simple_baseline || !Array.isArray(r.evidence_graph?.nodes) || !r.evidence_graph.nodes.length || r.evidence_graph.nodes.length > 200 || !r.falsification?.checks?.length || !r.shift) throw new Error("Incomplete research receipt");
    const p = r.quant.probabilities;
    if (![p.up, p.down, p.flat, r.simple_baseline.p_up, r.simple_baseline.p_down, r.shift.p_up].every(Number.isFinite)) throw new Error("Invalid baseline numbers");
    if (![p.up,p.down,p.flat].every(n => n >= 0 && n <= 1) || Math.abs(p.up+p.down+p.flat-1)>.002 || !Number.isInteger(r.event_contract.horizon_days) || r.event_contract.horizon_days<1 || r.event_contract.horizon_days>252) throw new Error("Invalid event probabilities or horizon");
    const check = r.falsification.checks[0];
    if (!Number.isFinite(check.threshold) || typeof check.reason !== "string" || ![r.name,r.as_of,r.symbol].every(x => typeof x === "string")) throw new Error("Invalid scenario description");
    const ids = new Set();
    for (const n of r.evidence_graph.nodes) {
      if (typeof n.id !== "string" || ids.has(n.id) || typeof n.text !== "string" || n.text.length>10000 || !["measurement","source","assumption","interpretation"].includes(n.kind)) throw new Error("Invalid evidence node");
      ids.add(n.id);
    }
    if (!Array.isArray(r.evidence_graph.edges) || r.evidence_graph.edges.length>10000 || !r.evidence_graph.edges.every(e => ids.has(e.from) && ids.has(e.to))) throw new Error("Invalid evidence connections");
    const s = r.demo_settlement;
    if (s && (!["UP","DOWN","SIDEWAYS"].includes(s.outcome) || !Number.isFinite(s.scores?.brier_multiclass) || typeof s.falsification?.status !== "string")) throw new Error("Invalid synthetic outcome");
    return b;
  }
  function fan(r) {
    const svg = $("fan"), width = Math.max(230, svg.clientWidth || 600), h = r.event_contract.horizon_days;
    const series = window.TradefloorView.series(r, state.chartMode), a = series.scenario, b = series.baseline;
    const index = Math.max(0, Math.min(a.length - 1, state.chartIndex ?? a.length - 1));
    const point = a[index], reference = window.TradefloorView.nearest(b, point.day);
    const format = value => state.chartMode === "price" ? value.toFixed(2) : signed(value);
    const vals = [...a, ...b].flatMap(p => [p.p10, p.p90]);
    let lo = Math.min(...vals), hi = Math.max(...vals); const pad = (hi - lo) * .15 || 1; lo -= pad; hi += pad;
    const x = d => 53 + d / h * (width - 70), y = v => 210 - (v - lo) / (hi - lo) * 185;
    svg.replaceChildren(); svg.setAttribute("viewBox", `0 0 ${width} 245`);
    svg.setAttribute("aria-label", `${state.chartMode === "price" ? "Price in quote units" : "Return percent"} distribution, day ${point.day}: median ${format(point.p50)}, 10–90% range ${format(point.p10)} to ${format(point.p90)}`);
    const draw = (name, attrs, text) => { const n = document.createElementNS("http://www.w3.org/2000/svg", name); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v); if (text !== undefined) n.textContent = text; svg.append(n); return n; };
    for (let i = 0; i <= 4; i++) { const value = lo + (hi - lo) * i / 4; draw("line", { x1: 53, x2: width - 17, y1: y(value), y2: y(value), stroke: "#26343e", "stroke-dasharray": "2 5" }); draw("text", { x: 0, y: y(value) + 3 }, format(value)); }
    draw("polygon", { points: [...a.map(p => `${x(p.day)},${y(p.p90)}`), ...a.slice().reverse().map(p => `${x(p.day)},${y(p.p10)}`)].join(" "), fill: "#80d5b516" });
    for (const bound of ["p10", "p90"]) draw("polyline", { points: a.map(p => `${x(p.day)},${y(p[bound])}`).join(" "), fill: "none", stroke: "#80d5b535", "stroke-width": 1 });
    for (const [data, color, dash] of [[b, "#88b9e0", "4 4"], [a, "#80d5b5", "none"]]) draw("polyline", { points: data.map(p => `${x(p.day)},${y(p.p50)}`).join(" "), fill: "none", stroke: color, "stroke-width": 2, "stroke-dasharray": dash });
    const ticks = width < 400 ? [0, Math.round(h/2), h] : [0, ...r.scenario.fan.map(p => p.day)];
    let lastLabel = -100;
    for (const d of ticks) { if (x(d)-lastLabel < 36 && d !== h) continue; if (d !== h && x(h)-x(d)<32) continue; draw("text", { x: x(d), y: 236, "text-anchor": "middle" }, d === h ? `${d}d` : String(d)); lastLabel = x(d); }
    draw("line", { x1: x(point.day), x2: x(point.day), y1: 20, y2: 211, stroke: "#d5b78465", "stroke-dasharray": "3 4" });
    draw("circle", { cx: x(point.day), cy: y(point.p50), r: 4, fill: "#80d5b5", stroke: "#0b1016", "stroke-width": 2 });
    $("chart-day").max = a.length - 1; $("chart-day").value = index;
    $("chart-day").setAttribute("aria-valuetext", `Trading day ${point.day}`);
    set("chart-readout", `DAY ${point.day} · Median ${format(point.p50)} · Range ${format(point.p10)} to ${format(point.p90)} · Baseline ${format(reference.p50)}${state.chartMode === "price" ? " · quote units" : ""}`);
    for (const mode of ["return", "price"]) $("chart-" + mode).setAttribute("aria-pressed", String(mode === state.chartMode));
  }
  for (const mode of ["return", "price"]) $("chart-" + mode).addEventListener("click", () => { state.chartMode = mode; if (state.current) fan(state.current.result); });
  $("chart-day").addEventListener("input", () => { state.chartIndex = Number($("chart-day").value); if (state.current) fan(state.current.result); });
  $("fan").addEventListener("pointermove", event => {
    if (!state.current || event.pointerType === "touch") return;
    const r = state.current.result, rect = $("fan").getBoundingClientRect();
    const day = Math.max(0, Math.min(r.event_contract.horizon_days, (event.clientX - rect.left - 53) / (rect.width - 70) * r.event_contract.horizon_days));
    const rows = window.TradefloorView.series(r).scenario, nearest = window.TradefloorView.nearest(rows, day), index = rows.indexOf(nearest);
    if (state.chartIndex !== index) { state.chartIndex = index; fan(r); }
  });
  function renderBrief(r, bundle) {
    const summary = window.TradefloorView.summary(r);
    set("brief-heading", summary.direction === "SIDEWAYS" ? "A divided outlook." : summary.direction === "UP" ? "An upward tilt." : "A downward tilt.");
    set("brief-text", `The reaction assumptions ${summary.shiftPoints >= 0 ? "raise" : "lower"} P(UP) by ${Math.abs(summary.shiftPoints).toFixed(1)} points versus no reaction. This is a conditional model comparison, not a trading signal.`);
    $("brief-signals").replaceChildren();
    for (const [label, value, review] of [["Direction rule", "±8 pt UP–DOWN gap", false], ["Evidence / assumptions", `${summary.sources} / ${summary.assumptions}`, false], ["Review flags", String(summary.review), summary.review > 0]]) {
      const row = el("div", undefined, "signal" + (review ? " review" : "")); row.append(el("span", label), el("strong", value)); $("brief-signals").append(row);
    }
    set("p-down", pct(r.scenario.p_down)); set("p-flat", pct(r.scenario.p_flat)); set("p-up-detail", pct(r.scenario.p_up));
    set("event-band", `SIDEWAYS: ${signed(summary.flatLower)} to ${signed(summary.flatUpper)} at the ${r.event_contract.horizon_days}-day horizon.`);
    set("session-label", state.preview ? "Imported preview · unverified" : "Frozen experiment");
    set("session-meta", `${bundle.request.worlds} WORLDS / ${r.event_contract.horizon_days} DAYS / SEED ${bundle.request.seed}`);
    for (const button of document.querySelectorAll("[data-case]")) { const active = button.dataset.case === bundle.request.case; button.classList.toggle("active", active); button.setAttribute("aria-pressed", String(active)); }
  }
  function probabilityRows(rows, id = "baselines") {
    $(id).replaceChildren();
    for (const [name, p] of rows) {
      const row = el("div", undefined, "baseline-row"), bar = el("div", undefined, "prob-bar");
      bar.setAttribute("role", "img"); bar.setAttribute("aria-label", `DOWN ${pct(p.down)}, FLAT ${pct(p.flat)}, UP ${pct(p.up)}`);
      for (const cls of ["down", "flat", "up"]) { const part = el("span", undefined, cls); part.style.width = pct(p[cls]); bar.append(part); }
      row.append(el("span", name), bar, el("strong", pct(p.up))); $(id).append(row);
    }
  }
  function render(response, preview = false) {
    const b = validate(response), r = response.result;
    state.current = response; state.preview = preview; state.chartIndex = null;
    state.branches.set(b.id, { response, label: `${r.name} · ${b.request.sentiment >= 0 ? "+" : ""}${b.request.sentiment}` });
    $("case").value = b.request.case;
    const base = { earnings: [.6, 5], policy: [-.5, 12], liquidity: [-.75, 3] }[b.request.case];
    const presets = { original: [base[0], base[1], .2], fades: [base[0], 1, .2], persistent: [base[0], 20, .2], "small-retail": [base[0], base[1], .1], "large-retail": [base[0], base[1], .5], reverse: [-base[0], base[1], .2], neutral: [0, base[1], .2] };
    $("preset").value = Object.keys(presets).find(k => presets[k].every((x, i) => x === [b.request.sentiment, b.request.persistence, b.request.retail_weight][i])) || "custom";
    $("sentiment").value = b.request.sentiment; $("persistence").value = b.request.persistence; $("retail").value = b.request.retail_weight;
    set("case-name", r.name); set("headline", r.evidence_graph.nodes[0].text); set("data-kind", r.symbol === "SYNTHETIC" ? "SYNTHETIC EXAMPLE" : "USER-SUPPLIED DATA");
    set("p-up", pct(r.scenario.p_up)); set("median", signed(r.scenario.return_pct.p50));
    set("shift", `${r.shift.p_up >= 0 ? "+" : ""}${(r.shift.p_up * 100).toFixed(1)} pts vs no reaction`);
    set("range", `${signed(r.scenario.return_pct.p10)} to ${signed(r.scenario.return_pct.p90)} · 10–90%`);
    const diff = r.scenario.p_up - r.scenario.p_down; set("direction", diff >= .08 ? "UP" : diff <= -.08 ? "DOWN" : "SIDEWAYS");
    set("run-meta", `${r.event_contract.horizon_days} trading days · ${b.request.worlds} worlds · seed ${b.request.seed} · frozen ${r.as_of}`);
    set("receipt-id", b.id); set("receipt-trust", preview ? "Unverified imported preview. Verify with the local CLI before relying on it." : "Content hash and local receipt. No verified external timestamp or authorship.");
    probabilityRows([["Scenario / reaction", { up: r.scenario.p_up, down: r.scenario.p_down, flat: r.scenario.p_flat }], ["No-reaction swarm", { up: r.baseline.p_up, down: r.baseline.p_down, flat: r.baseline.p_flat }], ["Price-only quant", r.quant.probabilities], ["Student-t baseline", { up: r.simple_baseline.p_up, down: r.simple_baseline.p_down, flat: 1 - r.simple_baseline.p_up - r.simple_baseline.p_down }]]);
    set("failure", r.falsification.checks[0].reason + " Horizon threshold: " + Number(r.falsification.checks[0].threshold).toFixed(2));
    $("reveal").hidden = !r.demo_settlement; $("settlement").hidden = true;
    for (const id of ["challenge-result", "priorities", "arena-result"]) $(id).replaceChildren();
    renderBrief(r, b); fan(r); renderBranches(); renderEvidence(); busy(state.busy);
    status(preview ? "Opened an unverified receipt preview." : "Frozen run loaded. Edit an assumption, fork it, or search for a counterexample.");
  }
  async function attach() {
    if (!state.project || offline) return;
    const b = JSON.parse(state.current.bundle_json);
    state.project = await api("research_project", { action: "attach", project_id: state.project.id, body: { revision: state.project.revision, run_id: b.id, label: `${b.request.case} · reaction ${b.request.sentiment}` } });
    renderBranches();
  }
  async function run(fork = false) {
    await guarded(async () => {
      status("Computing a frozen scenario…");
      const c = $("case").value, preset = $("preset").value;
      let response;
      if (offline) {
        response = window.DEMO_DATA[`${c}:${preset}`];
        if (!response) throw new Error("Custom assumptions require the local workspace.");
      } else if (preset === "custom") {
        const values = { sentiment: Number($("sentiment").value), persistence: Number($("persistence").value), retail_weight: Number($("retail").value) };
        if (![...$("assumptions").querySelectorAll("input")].every(n => n.value !== "" && n.checkValidity())) throw new Error("Check the assumption values and limits.");
        if (fork && state.current) response = await api("fork", { run_id: state.current.result.run.run_id, overrides: values });
        else {
          const job = await api("research_job", { action: "submit", kind: "scenario", arguments: { case: c, ...values }, idempotency_key: crypto.randomUUID() });
          await followJob(job, async result => { render(await api("load_run", { run_id: result.run.run_id })); await attach(); });
          return;
        }
      } else {
        const res = await fetch("/api/scenario", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ case: c, preset, action: fork ? "fork" : "simulate", run_id: state.current?.result.run.run_id }) });
        response = await res.json(); if (!res.ok || response.error) throw new Error(response.error || "Scenario failed");
      }
      render(response); await attach();
      if (offline && fork) status("Opened a precomputed fork of the example's original thesis.");
    });
  }
  for (const button of document.querySelectorAll("[data-case]")) button.addEventListener("click", () => { if (state.busy) return; $("case").value = button.dataset.case; $("preset").value = "original"; run(false); });
  $("inspect-evidence").addEventListener("click", () => { tab("evidence"); $("main").focus(); });
  $("run").addEventListener("click", () => run(false)); $("fork").addEventListener("click", () => run(true));
  $("mobile-controls").addEventListener("click", () => { const open = $("research-controls").classList.toggle("open"); $("mobile-controls").setAttribute("aria-expanded", String(open)); });
  $("case").addEventListener("change", () => { $("preset").value = "original"; run(false); });
  $("preset").addEventListener("change", () => { status("Assumptions selected. Results still show the loaded run until you run or fork."); busy(false); });
  for (const id of ["sentiment", "persistence", "retail"]) $(id).addEventListener("input", () => { $("preset").value = "custom"; status("Draft assumptions. Run or fork to apply them."); busy(false); });
  $("reveal").addEventListener("click", () => { const s = state.current?.result.demo_settlement; if (!s || state.busy) return; set("settlement", `Synthetic outcome: ${s.outcome}. Multiclass Brier: ${s.scores.brier_multiclass.toFixed(3)}. Thesis ${s.falsification.status}. This is a demonstration, not a performance benchmark.`); $("settlement").hidden = false; });
  async function refreshProjects(selected) {
    if (offline) return;
    const data = await api("research_project"); $("project-select").replaceChildren(el("option", "Unsaved session")); $("project-select").firstChild.value = "";
    for (const p of data.projects) { const option = el("option", p.title); option.value = p.id; $("project-select").append(option); }
    $("project-select").value = selected || "";
  }
  async function loadProject(id) {
    state.project = id ? await api("research_project", { action: "get", project_id: id }) : null;
    state.branches.clear(); remember("tradefloor.project", id || "");
    if (state.project) {
      $("question").value = state.project.question;
      if (state.project.runs.length) {
        for (const row of state.project.runs) state.branches.set(row.id, { label: row.label });
        render(await api("load_run", { run_id: state.project.runs.at(-1).id }));
      }
    }
    renderBranches(); renderEvidence(); status(state.project ? "Project reopened with its saved branches and evidence." : "Unsaved session opened.");
  }
  $("project-select").addEventListener("change", () => guarded(() => loadProject($("project-select").value)));
  $("save-project").addEventListener("click", () => guarded(async () => {
    if (offline) throw new Error("Save persistent projects in the local workspace. You can export individual demo receipts here.");
    const title = $("question").value.trim(); if (!title) throw new Error("Enter a research question.");
    if (!state.project) state.project = await api("research_project", { action: "create", body: { title, question: title } });
    else state.project = await api("research_project", { action: "update", project_id: state.project.id, body: { revision: state.project.revision, title, question: title } });
    await attach(); remember("tradefloor.project", state.project.id); await refreshProjects(state.project.id); status("Project saved. Your current branch is attached.");
  }));
  function renderBranches() {
    const list = state.project?.runs || [...state.branches].map(([id, row]) => ({ id, label: row.label }));
    set("branch-count", list.length); $("branches").replaceChildren();
    if (!list.length) $("branches").append(el("p", "Run an example to start a branch history.", "muted"));
    for (const row of list) {
      const line = el("div", undefined, "branch-row"), check = el("input"), label = el("label"), open = el("button", "Open", "secondary");
      check.type = "checkbox"; check.value = row.id; check.id = "branch-" + row.id; label.htmlFor = check.id;
      label.append(el("span", row.label), el("small", row.id));
      open.addEventListener("click", () => guarded(async () => { const data = state.branches.get(row.id)?.response || await api("load_run", { run_id: row.id }); render(data); tab("thesis"); }));
      line.append(check, label, open); $("branches").append(line);
    }
  }
  $("compare").addEventListener("click", () => guarded(async () => {
    const ids = [...$("branches").querySelectorAll("input:checked")].map(n => n.value);
    if (ids.length < 2 || ids.length > 4) throw new Error("Select two to four branches.");
    let result;
    if (offline) {
      const bundles = ids.map(id => JSON.parse(state.branches.get(id).response.bundle_json)), first = bundles[0];
      if (bundles.some(b => JSON.stringify(b.result.event_contract) !== JSON.stringify(first.result.event_contract) || JSON.stringify(b.inputs.prices) !== JSON.stringify(first.inputs.prices))) throw new Error("These branches have different events or frozen histories.");
      result = { rows: bundles.map(b => ({ id: b.id, probabilities: { up: b.result.scenario.p_up, down: b.result.scenario.p_down, flat: b.result.scenario.p_flat }, delta_p_up: b.result.scenario.p_up - first.result.scenario.p_up, changes: Object.keys(b.request).filter(k => JSON.stringify(b.request[k]) !== JSON.stringify(first.request[k])).map(k => ({ field: k, before: first.request[k], after: b.request[k] })), randomness_pairing: "precomputed example; inspect receipt" })) };
    } else result = await api("compare_runs", { run_ids: ids });
    table("comparison-result", ["Run", "P(UP)", "Change", "Changed assumptions"], result.rows.map(r => [r.id.slice(0, 8), pct(r.probabilities.up), (r.delta_p_up * 100).toFixed(1) + " pts", r.changes.map(c => `${c.field}: ${JSON.stringify(c.before)} → ${JSON.stringify(c.after)}`).join("; ") || "Original"]));
    for (const r of result.rows) $("comparison-result").append(el("p", `${r.id.slice(0, 8)} · ${r.randomness_pairing}`, "small muted"));
    status("Compared branches on identical frozen history and event definitions.");
  }));
  async function followJob(job, onResult) {
    state.job = job.id; busy(true); $("job-status").hidden = false;
    const untilDone = async () => {
      const next = await api("research_job", { action: "get", job_id: job.id });
      set("job-text", `${next.kind}: ${next.state}`); $("job-progress").value = next.progress.total ? next.progress.done / next.progress.total : 0;
      if (["completed", "failed", "cancelled"].includes(next.state)) {
        state.job = null; $("job-status").hidden = true;
        if (next.state === "completed") await onResult(next.result);
        else status(next.error || `Research job ${next.state}.`, next.state === "failed");
        busy(false);
        return;
      }
      await new Promise(resolve => setTimeout(resolve, 600));
      await untilDone();
    };
    try { await untilDone(); } catch (e) { state.job = null; $("job-status").hidden = true; busy(false); throw e; }
  }
  async function submit(kind, args, callback) {
    status(`Running ${kind.replaceAll("_", " ")} research job. Progress and cancellation are shown above the workspace tabs.`);
    const job = await api("research_job", { action: "submit", kind, arguments: args, idempotency_key: crypto.randomUUID() });
    await followJob(job, callback);
  }
  $("cancel-job").addEventListener("click", async () => { try { if (state.job) await api("research_job", { action: "cancel", job_id: state.job }); } catch (e) { status(e.message, true); } });
  function challengeResult(result) {
    const box = $("challenge-result"); box.replaceChildren(el("p", result.status));
    if (result.counterexample) {
      const c = result.counterexample; box.append(el("p", `${result.original_direction} → ${c.direction}`, "result-row"), el("p", Object.entries(c.assumptions).map(([k, v]) => `${k}: ${Number(v).toFixed(2)}`).join(" · "), "small"));
      if (result.run) { const button = el("button", "Open counterexample", "secondary"); button.addEventListener("click", () => guarded(async () => { const response = offline ? state.branches.get(result.run.run_id).response : await api("load_run", { run_id: result.run.run_id }); render(response); await attach(); })); box.append(button); }
    }
    box.append(el("p", `${result.evaluated} candidates evaluated. ${result.limits}`, "small muted")); status("Counterexample search finished. Its result is conditional on the model and search bounds.");
  }
  $("challenge").addEventListener("click", () => guarded(async () => {
    if (offline) {
      const original = JSON.parse(state.current.bundle_json), dir = r => r.scenario.p_up - r.scenario.p_down >= .08 ? "UP" : r.scenario.p_up - r.scenario.p_down <= -.08 ? "DOWN" : "SIDEWAYS";
      const candidates = Object.entries(window.DEMO_DATA).filter(([k]) => k.startsWith(original.request.case + ":"));
      const found = candidates.find(([, r]) => dir(r.result) !== dir(state.current.result));
      let counterexample = null, run = null;
      if (found) { const r = found[1], b = JSON.parse(r.bundle_json); state.branches.set(b.id, { response: r, label: found[0] }); counterexample = { direction: dir(r.result), assumptions: { sentiment: b.request.sentiment, persistence: b.request.persistence, retail_weight: b.request.retail_weight } }; run = r.result.run; renderBranches(); }
      challengeResult({ status: found ? "Reversal found among seven example presets" : "No reversal among the example presets", original_direction: dir(state.current.result), counterexample, run, evaluated: candidates.length, limits: "Preset comparison only. Local mode searches a bounded parameter grid." });
    } else {
      const req = JSON.parse(state.current.bundle_json).request;
      const bounds = { sentiment: [-1, 1], persistence: [Math.min(1, req.persistence), Math.max(20, req.persistence)], retail_weight: [Math.min(.1, req.retail_weight), Math.max(.5, req.retail_weight)] };
      await submit("challenge", { run_id: state.current.result.run.run_id, bounds }, challengeResult);
    }
  }));
  $("investigate").addEventListener("click", () => guarded(() => submit("investigate", { run_id: state.current.result.run.run_id }, r => { $("priorities").replaceChildren(); for (const row of r.ranking) { const n = el("div", undefined, "result-row"); n.append(el("strong", row.assumption), el("p", `${(row.sensitivity * 100).toFixed(1)} probability points across tested endpoints`)); $("priorities").append(n); } $("priorities").append(el("p", "Sensitivity ranking, not expected information value. Interactions excluded.", "small muted")); status("Research priorities computed from explicit assumption ranges."); })));
  $("arena").addEventListener("click", () => guarded(() => submit("arena", { run_id: state.current.result.run.run_id }, r => { table("arena-result", ["Model", "P(UP)", "P(DOWN)", "P(FLAT)", "Latency"], r.forecasts.map(x => [x.model_id, pct(x.probabilities.up), pct(x.probabilities.down), pct(x.probabilities.flat), x.latency_ms.toFixed(1) + " ms"])); $("arena-result").append(el("p", r.note, "small muted")); status("Model forecasts computed. Ranking skill requires matured outcomes."); })));
  $("scoreboard").addEventListener("click", () => guarded(async () => { const r = await api("scoreboard"); jsonResult("scoreboard-result", r); status("Loaded the complete local experiment registry."); }));
  function activeGraph() { return state.project?.graph || state.current?.result.evidence_graph; }
  function renderEvidence() {
    const graph = activeGraph(); $("evidence-nodes").replaceChildren(); $("evidence-inspector").hidden = true;
    if (!graph) return;
    set("evidence-note", `${state.project?.graph ? "Project evidence" : "Loaded run evidence"} · ${graph.source_family_count ?? "unknown"} declared source families. Source independence remains unverified.`);
    for (const node of graph.nodes) {
      const button = el("button", undefined, "evidence-node" + (node.status && node.status !== "active" ? " review" : ""));
      button.append(el("strong", `${node.id} / ${node.kind}`), el("span", node.text), el("small", node.status || "active"));
      const edges = graph.edges.filter(e => e.to === node.id); if (edges.length) button.append(el("small", edges.map(e => `${e.from} → ${e.kind}`).join(" · ")));
      button.addEventListener("click", () => {
        const detail = $("evidence-inspector"); detail.hidden = false; detail.replaceChildren(el("h3", `${node.id} · ${node.kind}`), el("p", node.text));
        for (const key of ["source", "source_family", "published_at", "available_at", "availability_status", "document_sha256", "status"]) if (node[key]) detail.append(el("p", `${key.replaceAll("_", " ")}: ${node[key]}`, "small muted"));
        if (node.anchor) detail.append(el("pre", `Exact document span ${node.anchor.start}–${node.anchor.end}\n${node.anchor.document_text}`));
        const supporting = graph.edges.filter(e => e.from === node.id); if (supporting.length) detail.append(el("p", "Dependent claims: " + supporting.map(e => e.to).join(", ")));
        if (state.project?.graph && node.kind !== "interpretation" && !offline) { const retract = el("button", node.status === "retracted" ? "Restore evidence" : "Retract evidence", "secondary"); retract.addEventListener("click", () => guarded(async () => { const rows = state.project.evidence.map(e => e.id === node.id ? { ...e, status: node.status === "retracted" ? "active" : "retracted" } : e); await updateEvidence(rows, state.project.claims); status("Evidence status saved. Dependent claims are marked for review."); })); detail.append(retract); }
      }); $("evidence-nodes").append(button);
    }
  }
  async function updateEvidence(rows, claims, cutoff) {
    if (!state.project) throw new Error("Save this research to a project first.");
    state.project = await api("research_project", { action: "update", project_id: state.project.id, body: { revision: state.project.revision, evidence: rows, claims, cutoff: cutoff || state.project.cutoff } }); renderEvidence();
  }
  $("use-evidence").addEventListener("click", () => guarded(async () => { if (!state.current) throw new Error("Load a scenario first."); const g = state.current.result.evidence_graph; await updateEvidence(g.nodes.filter(n => n.kind !== "interpretation"), g.nodes.filter(n => n.kind === "interpretation"), g.cutoff); status("Copied the frozen evidence into the editable project. The receipt remains preserved."); }));
  $("freeze-evidence").addEventListener("click", () => guarded(async () => {
    if (!state.project || !state.current) throw new Error("Save a project and load a scenario first.");
    await submit("project_scenario", { project_id: state.project.id, run_id: state.current.result.run.run_id }, async r => {
      render(await api("load_run", { run_id: r.run.run_id })); await attach();
      status("Project evidence frozen into a new branch. Returns use the same numerical assumptions; text is not an automatic probability adjustment.");
    });
  }));
  $("evidence-form").addEventListener("submit", event => { event.preventDefault(); guarded(async () => { if (!state.project) throw new Error("Save a project first."); const kind = $("evidence-kind").value, stamp = $("evidence-available").value ? new Date($("evidence-available").value + "Z").toISOString() : null; if (kind !== "assumption" && !stamp) throw new Error("Dated evidence needs a publication/availability timestamp."); const row = { id: $("evidence-id").value.trim(), kind, text: $("evidence-text").value, source_family: $("evidence-family").value || undefined, published_at: stamp, available_at: stamp }; await updateEvidence([...state.project.evidence, row], state.project.claims); $("evidence-form").reset(); status("Evidence saved with asserted availability and source lineage."); }); });
  $("claim-form").addEventListener("submit", event => { event.preventDefault(); guarded(async () => { if (!state.project) throw new Error("Save a project first."); const claim = { id: "H-" + crypto.randomUUID().slice(0, 8), text: $("claim-text").value, evidence_ids: $("claim-refs").value.split(",").map(s => s.trim()).filter(Boolean) }; await updateEvidence(state.project.evidence, [...state.project.claims, claim]); $("claim-form").reset(); status("Claim linked to its supporting evidence."); }); });
  $("query-timeline").addEventListener("click", () => guarded(async () => { const cutoff = new Date($("cutoff").value + "Z").toISOString(); const r = await api("information_timeline", { cutoff, series: $("series").value.trim() || null }); table("timeline-result", ["Series", "Observation", "Value", "Available", "Status"], r.records.map(x => [x.series, x.observation_key, typeof x.value === "object" ? JSON.stringify(x.value) : x.value, x.available_at, x.availability_status])); $("timeline-result").append(el("p", `${r.records.length} eligible records · ${r.excluded.unknown_availability} unknown · ${r.excluded.later_availability} later. ${r.note}`, "small muted")); status("Timeline queried at the selected cutoff."); }));
  $("fetch-source").addEventListener("click", () => guarded(() => submit("fetch", { provider: $("provider").value, identifier: $("provider-id").value.trim(), vintage: $("vintage").value || null }, r => status(`Captured ${r.count} source records. ${r.scope}`))));
  $("document-diff").addEventListener("click", () => guarded(async () => { const r = await api("document_changes", { before: $("before-document").value, after: $("after-document").value }); table("document-result", ["Change", "Earlier text", "Later text"], r.changes.map(c => [c.kind, c.before, c.after])); $("document-result").append(el("p", r.note, "small muted")); status("Document differences computed with exact spans."); }));
  const examples = {
    factor_stress: { holdings: [{ symbol: "EXAMPLE", value: 10000, currency: "USD", loadings: { rates: -2, equity: 1 } }], shocks: { rates: .01, equity: -.1 }, account_currency: "USD" },
    portfolio_allocate: { covariance: [[.04, .005], [.005, .01]], max_weight: .8 },
    option_implied: { spot: 100, volatility: .2, years: 1, quote_as_of: "2026-09-28T16:00:00Z", flat_band: .02 },
    robust_evaluation: { cases: [{ as_of: "2026-09-28", probabilities: { up: .5, down: .3, flat: .2 }, reference: { up: .4, down: .4, flat: .2 }, outcome: "UP" }], block_length: 5 },
    research_record: { kind: "protocol", payload: { name: "My prospective study", schedule: "Every trading-day close", primary_endpoint: "Paired multiclass Brier loss", settlement_rule: "Saved event contract and completed adjusted bars", trial_budget: 10, universe: ["AAPL", "MSFT"], training_label_end: "2026-09-28T23:59:59Z", holdout_start: "2026-10-12T00:00:00Z" } },
    research_memory: { cutoff: "2026-10-11T23:59:59Z" },
    information_timeline: { cutoff: "2026-09-28T23:59:59Z", records: [{ series: "EXAMPLE", observation_key: "2026-09", value: 100, source: "synthetic", rights: "synthetic", effective_at: "2026-09-01T00:00:00Z", published_at: "2026-09-28T12:00:00Z", available_at: "2026-09-28T12:00:00Z", retrieved_at: "2026-09-28T12:00:00Z" }] },
    market_diagnostics: { tape: [{ last: 100, bid: 99, ask: 101 }, { last: 101, bid: 100, ask: 102 }] }
  };
  $("tool-name").addEventListener("change", () => { $("tool-arguments").value = JSON.stringify(examples[$("tool-name").value], null, 2); });
  $("tool-arguments").value = JSON.stringify(examples.factor_stress, null, 2);
  $("execute-tool").addEventListener("click", () => guarded(async () => { jsonResult("tool-result", await api($("tool-name").value, JSON.parse($("tool-arguments").value))); status("Research tool completed on supplied inputs."); }));
  function download(value, filename) { const url = URL.createObjectURL(new Blob([typeof value === "string" ? value : JSON.stringify(value)], { type: "application/json" })); const a = el("a"); a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
  $("export-run").addEventListener("click", () => { if (state.current) download(state.current.bundle_json, "tradefloor-" + state.current.result.run.run_id + ".json"); });
  for (const [id, include] of [["export-project", true], ["export-summary", false]]) $(id).addEventListener("click", () => guarded(async () => { if (!state.project) throw new Error("Save a project first."); download(await api("project_export", { project_id: state.project.id, include_data: include }), "tradefloor-project" + (include ? "" : "-summary") + ".json"); status(include ? "Exported project with source data. Review rights before sharing." : "Exported a summary without source data."); }));
  for (const kind of ["run", "project"]) $("open-" + kind).addEventListener("click", () => { state.importing = kind; $("file").click(); });
  $("file").addEventListener("change", event => { const file = event.target.files[0]; if (!file) return; guarded(async () => { if (file.size > (state.importing === "project" ? 20000000 : 2000000)) throw new Error("File exceeds import size limit."); const raw = await file.text(), b = JSON.parse(raw); if (state.importing === "project") { const p = await api("project_bundle", { payload: b }); await refreshProjects(p.id); await loadProject(p.id); } else if (offline) { render({ result: { ...b.result, run: { run_id: b.id, sha256: b.sha256 } }, bundle_json: raw }, true); } else { const res = await fetch("/api/scenario", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action: "import", bundle_json: raw }) }); const data = await res.json(); if (!res.ok || data.error) throw new Error(data.error); render(data); await attach(); } }).finally(() => { event.target.value = ""; }); });
  if (typeof ResizeObserver !== "undefined") new ResizeObserver(() => { if (state.current && !$("view-thesis").hidden) fan(state.current.result); }).observe($("fan"));
  const commands = [
    ["Thesis · inspect the scenario", "thesis"], ["Branches · compare saved runs", "compare"],
    ["Model arena · compare forecasts", "models"], ["Evidence · inspect sources and claims", "evidence"],
    ["Information timeline · what was known when", "timeline"], ["Research tools · documents, portfolio and evaluation", "tools"],
    ["Export current run receipt", null, "export-run"], ["Find a counterexample", "thesis", "challenge"],
    ["Rank the unknowns", "thesis", "investigate"]
  ];
  function searchCommands() {
    const query = $("command-search").value.toLowerCase().trim(); $("command-results").replaceChildren();
    for (const [label, view, action] of commands.filter(([label]) => label.toLowerCase().includes(query))) {
      const button = el("button", label);
      button.disabled = Boolean(action && $(action).disabled);
      button.addEventListener("click", () => { $("command-dialog").close(); if (view) tab(view); if (action) $(action).click(); $("main").focus(); });
      $("command-results").append(button);
    }
    if (!$("command-results").children.length) $("command-results").append(el("p", "No matching tools. Try evidence, model or compare.", "muted"));
  }
  function openCommands() { if ($("command-dialog").open) return; $("command-search").value = ""; searchCommands(); $("command-dialog").showModal(); $("command-search").focus(); }
  $("open-command").addEventListener("click", openCommands);
  $("close-command").addEventListener("click", () => $("command-dialog").close());
  $("command-search").addEventListener("input", searchCommands);
  $("command-search").addEventListener("keydown", event => { if (event.key === "Enter") { event.preventDefault(); $("command-results").querySelector("button:not(:disabled)")?.click(); } });
  document.addEventListener("keydown", event => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); openCommands(); } });
  async function init() {
    if (offline) {
      set("connection", "STANDALONE DEMO"); set("mode-note", "Seven frozen assumption sets per example. Projects, custom runs and research tools need the local workspace.");
      $("assumptions").disabled = true; $("preset").querySelector('[value="custom"]').disabled = true;
      render(window.DEMO_DATA["earnings:original"]); return;
    }
    try {
      await refreshProjects(); const previous = recalled("tradefloor.project");
      if (previous && [...$("project-select").options].some(o => o.value === previous)) { $("project-select").value = previous; await loadProject(previous); }
      if (!state.current) await run(false);
      const pending = await api("research_job"); const job = pending.jobs.find(j => ["running", "queued"].includes(j.state));
      if (job) status(`An earlier ${job.kind} job is ${job.state}. Use the research_job CLI to inspect or cancel it.`);
    } catch (e) { status(e.message, true); busy(false); }
  }
  init();
})();
