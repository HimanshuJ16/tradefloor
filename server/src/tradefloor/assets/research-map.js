"use strict";
(() => {
  const W = window.TradefloorWorkspace, M = window.TradefloorMapModel;
  const $ = id => document.getElementById(id), svgNS = "http://www.w3.org/2000/svg";
  const state = { session: null, graph: null, selected: null, focus: null, cursor: null, playing: null, view: [0, 0, 1000, 620], inspectorKey: null, withdrawal: null, forking: false };
  const el = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = String(text); if (cls) n.className = cls; return n; };
  const svg = (tag, attributes = {}, text) => { const n = document.createElementNS(svgNS, tag); for (const [k, v] of Object.entries(attributes)) n.setAttribute(k, v); if (text !== undefined) n.textContent = text; return n; };
  const status = (text, error = false) => { $("map-action-status").textContent = text; $("map-action-status").classList.toggle("error", error); };
  function stop() { clearInterval(state.playing); state.playing = null; $("map-play").textContent = "Play replay"; }
  function reset() { state.focus = null; state.view = [0, 0, 1000, 620]; $("map-search").value = ""; $("map-filter").value = "all"; $("map-warnings").setAttribute("aria-pressed", "false"); }
  function select(id) { state.selected = id; state.withdrawal = null; state.inspectorKey = null; render(); }
  function inspect(n) {
    const signature = JSON.stringify([n, state.withdrawal, state.graph.imported, W.offline]);
    if (state.inspectorKey === signature) return;
    state.inspectorKey = signature;
    const box = $("map-inspector");
    box.replaceChildren(el("p", n.type.toUpperCase() + " / " + n.status, "eyebrow"), el("h3", n.label), el("p", n.text));
    if (n.detail?.probabilities) {
      const probabilities = el("div", undefined, "desk-probabilities");
      for (const [k, v] of Object.entries(n.detail.probabilities)) probabilities.append(el("span", k.toUpperCase() + " " + (100 * v).toFixed(1) + "%"));
      box.append(probabilities);
    }
    const details = el("details"); details.append(el("summary", "Inspect exact recorded details"), el("pre", JSON.stringify(n.detail, null, 2))); box.append(details);
    const related = state.graph.edges.filter(e => e.from === n.id || e.to === n.id);
    if (related.length) box.append(el("p", "Explicit connections", "eyebrow"));
    for (const e of related) {
      const id = e.from === n.id ? e.to : e.from, neighbor = state.graph.nodes.find(v => v.id === id);
      const button = el("button", (e.from === n.id ? "To " : "From ") + neighbor.label + " / " + e.relation, "secondary map-related");
      button.addEventListener("click", () => select(id)); box.append(button);
    }
    if (n.evidenceId && n.withdrawable) {
      const preview = el("button", "Preview withdrawal impact", "secondary");
      preview.addEventListener("click", () => { state.withdrawal = n.id; state.inspectorKey = null; render(); }); box.append(preview);
      if (state.withdrawal === n.id) {
        const affected = M.impact(state.graph, n.id);
        box.append(el("p", `${affected.length} dependent claims or forecasts in this checkpoint. This traces recorded references; it does not measure a causal effect or change any probabilities.`, "small"));
        for (const value of affected) box.append(el("p", value.label + " / " + value.text, "small"));
        box.append(el("p", "A new branch retracts this evidence and marks dependent scenario claims for review. Numerical assumptions and baselines remain unchanged. New research requires its own preview and Start.", "small muted"));
        const fork = el("button", "Create branch with evidence retracted", "secondary");
        fork.disabled = W.offline || state.graph.imported || state.forking;
        if (W.offline || state.graph.imported) box.append(el("p", W.offline ? "Branch creation requires the local workspace." : "Imported sessions remain untrusted data. Open a local scenario to create a branch.", "small muted"));
        fork.addEventListener("click", async () => {
          if (state.forking) return;
          const receipt = state.graph.receipt;
          state.forking = true; fork.disabled = true; status("Creating an evidence branch on the original frozen history...");
          try {
            const response = await W.api("evidence_fork", { run_id: receipt, evidence_id: n.evidenceId });
            $("map-source").value = "scenario"; state.selected = M.key("source", n.evidenceId); state.withdrawal = null; state.cursor = null; reset();
            W.render(response); render();
            status("Branch created. Evidence retracted; dependent scenario claims require review. Numerical assumptions are unchanged. No model calls were made.");
          } catch (e) { status(e.message, true); }
          finally { state.forking = false; fork.disabled = false; }
        }); box.append(fork);
      }
    }
    if (n.type === "branch" || n.type === "thesis") {
      const compare = el("button", "Compare scenario branches", "secondary"); compare.addEventListener("click", () => W.tab("compare")); box.append(compare);
    }
  }
  function render() {
    const session = $("map-source").value === "session" ? state.session : null;
    state.graph = M.build({ session, current: W.current(), cursor: state.cursor });
    const graph = state.graph;
    if (!graph.nodes.some(n => n.id === state.selected)) { state.selected = graph.nodes[0]?.id; state.withdrawal = null; }
    if (!graph.nodes.some(n => n.id === state.focus)) state.focus = null;
    const filtered = M.filter(graph, { query: $("map-search").value, group: $("map-filter").value, focus: state.focus, warnings: $("map-warnings").getAttribute("aria-pressed") === "true" });
    const focused = document.activeElement, focusedId = focused?.dataset.mapId;
    // Bound SVG complexity; the searchable list still contains every matching record.
    const visible = filtered.nodes.slice(0, 160);
    const selected = filtered.nodes.find(n => n.id === state.selected);
    if (selected && !visible.some(n => n.id === selected.id)) visible[visible.length - 1] = selected;
    const positioned = M.positions(visible), byId = new Map(positioned.map(n => [n.id, n]));
    const surface = $("map-svg"); surface.replaceChildren(); surface.setAttribute("viewBox", state.view.join(" "));
    const stars = svg("g", { class: "map-stars", "aria-hidden": "true" });
    for (let i = 0; i < 190; i++) stars.append(svg("circle", { cx: (i * 173.71) % 1000, cy: (i * 93.37) % 620, r: i % 7 === 0 ? 1.2 : .6, fill: i % 3 ? "#acc4df" : "#a7ddc6" }));
    surface.append(stars);
    const connections = svg("g", { "aria-hidden": "true" });
    let lineCount = 0;
    const orderedEdges = [...filtered.edges].sort((a, b) => Number(b.from === state.selected || b.to === state.selected) - Number(a.from === state.selected || a.to === state.selected));
    for (const edge of orderedEdges) {
      const a = byId.get(edge.from), b = byId.get(edge.to); if (!a || !b) continue;
      if (lineCount >= 1200) break;
      lineCount += 1;
      const path = svg("path", { d: `M${a.x},${a.y} Q${(a.x + b.x) / 2},${(a.y + b.y) / 2 - 22} ${b.x},${b.y}`, class: "map-edge" + (edge.warning ? " warning" : "") + (edge.from === state.selected || edge.to === state.selected ? " selected" : "") });
      connections.append(path);
    }
    surface.append(connections);
    const captions = svg("g", { class: "map-captions", "aria-hidden": "true" });
    for (const [text, x, y, group] of [["FROZEN INPUTS", 100, 210, "sources"], ["RESEARCH ROLES", 550, 40, "agents"], ["RECORDED CLAIMS", 765, 175, "findings"], ["CONDITIONAL FORECASTS", 395, 570, "forecasts"], ["OBJECTIONS & TESTS", 745, 590, "findings"]]) if (positioned.some(n => n.group === group)) captions.append(svg("text", { x, y }, text));
    surface.append(captions);
    for (const n of positioned) {
      const radius = n.type === "thesis" ? 17 : n.type === "agent" ? 10 : 6;
      const primary = ["thesis", "evidence", "assumption", "agent", "branch"].includes(n.type), left = n.x > 760;
      const group = svg("g", { transform: `translate(${n.x},${n.y})`, class: "map-node type-" + n.type + (!primary ? " map-secondary" : "") + (n.warning ? " warning" : "") + (n.id === state.selected ? " selected" : "") + (n.status === "working" ? " working" : ""), role: "button", tabindex: "0", "aria-label": `${n.type}: ${n.label}. ${n.status}. ${n.text}`, "aria-pressed": String(n.id === state.selected), "data-map-id": n.id });
      group.append(svg("circle", { r: radius + 8, class: "map-halo" }), svg("circle", { r: radius, class: "map-core" }), svg("text", { x: (radius + 10) * (left ? -1 : 1), y: -3, "text-anchor": left ? "end" : "start" }, n.label.length > 23 ? n.label.slice(0, 22) + "…" : n.label), svg("text", { x: (radius + 10) * (left ? -1 : 1), y: 11, "text-anchor": left ? "end" : "start", class: "map-node-status" }, n.status.slice(0, 27)));
      group.addEventListener("click", () => select(n.id));
      group.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(n.id); } }); surface.append(group);
    }
    if (focusedId && surface.contains(focused) === false) [...surface.querySelectorAll("[data-map-id]")].find(n => n.dataset.mapId === focusedId)?.focus({ preventScroll: true });
    $("map-empty").hidden = filtered.nodes.length > 0;
    const bounded = filtered.nodes.length > 160 || filtered.edges.length > lineCount;
    const count = `${filtered.nodes.length} of ${graph.nodes.length} records / ${filtered.edges.length} explicit connections` + (bounded ? `. Map shows ${visible.length} nodes and ${lineCount} lines; search, focus or use the complete list to inspect the rest.` : ".");
    $("map-count").textContent = count + (graph.receipt ? ` Receipt ${graph.receipt.slice(0, 8)}${session ? " / session " + session.id.slice(0, 8) : ""}.` : "");
    $("map-state").textContent = graph.imported ? "IMPORTED / UNTRUSTED" : session ? state.cursor === null ? session.state.toUpperCase() : "RECORDED REPLAY" : "FROZEN SCENARIO";
    $("map-focus").disabled = !state.selected;
    $("map-focus").textContent = state.focus ? "Show all connections" : "Focus connections";
    $("map-step").max = graph.events.length; $("map-step").value = graph.cursor;
    for (const id of ["map-step", "map-play", "map-live"]) $(id).disabled = !graph.events.length;
    const checkpoint = graph.events[graph.cursor - 1];
    $("map-checkpoint").textContent = checkpoint ? `Checkpoint ${graph.cursor} / ${graph.events.length}: ${checkpoint.kind.replaceAll("_", " ")}${checkpoint.body.role ? " / " + checkpoint.body.role : ""} / ${checkpoint.at || "time unspecified"}${graph.imported ? " / supplied archive" : ""}` : "Frozen inputs, before any recorded model calls.";
    const list = $("map-list"), listFocused = list.contains(document.activeElement) ? document.activeElement.dataset.mapId : null;
    list.replaceChildren();
    for (const n of filtered.nodes) {
      const button = el("button"); button.dataset.mapId = n.id; button.setAttribute("aria-pressed", String(n.id === state.selected)); button.append(el("strong", n.label), el("span", n.type + " / " + n.status), el("span", n.text.slice(0, 140)));
      button.addEventListener("click", () => select(n.id)); list.append(button);
    }
    if (listFocused) [...list.children].find(n => n.dataset.mapId === listFocused)?.focus({ preventScroll: true });
    const n = graph.nodes.find(n => n.id === state.selected); if (n) inspect(n);
  }
  function zoom(factor) {
    const [x, y, w, h] = state.view, width = Math.max(300, Math.min(1800, w * factor)), height = width * .62;
    state.view = [x + (w - width) / 2, y + (h - height) / 2, width, height]; $("map-svg").setAttribute("viewBox", state.view.join(" "));
  }
  let drag = null;
  $("map-svg").addEventListener("pointerdown", e => { if (e.target.closest(".map-node") || e.button !== 0) return; drag = { x: e.clientX, y: e.clientY, view: [...state.view] }; $("map-svg").setPointerCapture(e.pointerId); });
  $("map-svg").addEventListener("pointermove", e => { if (!drag) return; const rect = $("map-svg").getBoundingClientRect(), scale = Math.max(drag.view[2] / rect.width, drag.view[3] / rect.height); state.view = [drag.view[0] - (e.clientX - drag.x) * scale, drag.view[1] - (e.clientY - drag.y) * scale, drag.view[2], drag.view[3]]; $("map-svg").setAttribute("viewBox", state.view.join(" ")); });
  for (const name of ["pointerup", "pointercancel", "lostpointercapture"]) $("map-svg").addEventListener(name, () => { drag = null; });
  $("map-zoom-in").addEventListener("click", () => zoom(.8)); $("map-zoom-out").addEventListener("click", () => zoom(1.25));
  for (const id of ["map-search", "map-filter"]) $(id).addEventListener("input", render);
  $("map-focus").addEventListener("click", () => { state.focus = state.focus ? null : state.selected; render(); });
  $("map-warnings").addEventListener("click", () => { const n = $("map-warnings"); n.setAttribute("aria-pressed", String(n.getAttribute("aria-pressed") !== "true")); render(); });
  $("map-cinematic").addEventListener("click", () => { const n = $("map-cinematic"), on = n.getAttribute("aria-pressed") !== "true"; n.setAttribute("aria-pressed", String(on)); document.querySelector(".research-map").classList.toggle("cinematic", on); });
  $("map-list-toggle").addEventListener("click", () => { $("map-list").hidden = !$("map-list").hidden; $("map-list-toggle").setAttribute("aria-expanded", String(!$("map-list").hidden)); });
  $("map-reset").addEventListener("click", () => { reset(); render(); });
  $("map-source").addEventListener("change", () => { stop(); state.cursor = null; state.selected = null; state.withdrawal = null; reset(); render(); });
  $("map-step").addEventListener("input", () => { stop(); state.cursor = Number($("map-step").value); render(); });
  $("map-live").addEventListener("click", () => { stop(); state.cursor = null; render(); });
  $("map-play").addEventListener("click", () => {
    if (state.playing) { stop(); return; }
    if (state.cursor === null || state.cursor >= state.graph.events.length) state.cursor = 0;
    $("map-play").textContent = "Pause replay"; render();
    state.playing = setInterval(() => { state.cursor += 1; render(); if (state.cursor >= state.graph.events.length) stop(); }, 1100);
  });
  document.addEventListener("visibilitychange", () => { if (document.hidden) stop(); });
  new MutationObserver(() => { if ($("view-desk").hidden) stop(); }).observe($("view-desk"), { attributes: true, attributeFilter: ["hidden"] });
  document.addEventListener("tradefloor:run-loaded", () => { state.inspectorKey = null; render(); });
  for (const event of ["tradefloor:session-loaded", "tradefloor:plan-previewed"]) document.addEventListener(event, e => {
    const previous = state.session?.id;
    state.session = event === "tradefloor:plan-previewed" ? { id: e.detail.id, plan: e.detail, state: "preview", responses: [], events: [] } : e.detail;
    $("map-source").querySelector('[value="session"]').disabled = false;
    if (previous !== state.session.id) { stop(); state.cursor = null; state.selected = null; state.withdrawal = null; state.inspectorKey = null; reset(); $("map-source").value = "session"; }
    render();
  });
  render();
})();
