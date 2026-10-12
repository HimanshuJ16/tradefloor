"use strict";
(() => {
  const W = window.TradefloorWorkspace, $ = id => document.getElementById(id);
  const S = { profiles: [], recipes: [], sessions: [], datasets: [], plan: null, session: null, timer: null, loading: false, ready: false, initializing: false, pollGeneration: 0 };
  const roles = { quick: ["researcher", "risk"], balanced: ["researcher", "bull", "bear", "risk"], deep: ["researcher", "bull", "bear", "risk", "synthesizer"], chat: ["researcher"] };
  const node = (tag, value, cls) => { const e = document.createElement(tag); if (value !== undefined) e.textContent = value !== null && typeof value === "object" ? JSON.stringify(value) : String(value); if (cls) e.className = cls; return e; };
  const message = (id, value, error = false) => { $(id).textContent = value; $(id).classList.toggle("error", error); };
  const nullable = id => $(id).value.trim() === "" ? null : Number($(id).value);
  const utc = id => $(id).value ? $(id).value + ":00+00:00" : "";
  const pct = n => (100 * n).toFixed(1) + "%";
  const money = n => n === null || n === undefined ? "unknown" : "$" + Number(n).toFixed(4);
  async function action(statusId, fn) {
    if (S.initializing) { message(statusId, "The desk is loading its saved connections and records. Please wait."); return; }
    if (S.loading) { message(statusId, "Please wait for the current operation to finish."); return; }
    S.loading = true;
    const fields = statusId === "profile-status" ? $("profile-fields") : null;
    if (fields) fields.disabled = true;
    try { await fn(); } catch (e) { message(statusId, e.message, true); } finally { S.loading = false; if (fields) fields.disabled = W.offline; }
  }
  function selectOptions(select, rows, placeholder) {
    const previous = select.value; select.replaceChildren();
    if (placeholder !== undefined) { const e = node("option", placeholder); e.value = ""; select.append(e); }
    for (const r of rows) { const e = node("option", r.name || r.question); e.value = r.id; select.append(e); }
    if ([...select.options].some(e => e.value === previous)) select.value = previous;
  }
  function invalidate() { S.plan = null; $("desk-preview-result").hidden = true; $("desk-start").hidden = true; }
  function routing(saved = {}) {
    const prior = Object.fromEntries([...$("desk-routing").querySelectorAll("select")].map(e => [e.dataset.role, e.value]));
    $("desk-routing").replaceChildren(); const mode = $("desk-mode").value;
    $("desk-compare").hidden = mode !== "compare";
    if (mode === "compare") {
      const selected = new Set([...$("desk-compare").querySelectorAll("input:checked")].map(e => e.value));
      $("desk-compare").replaceChildren(node("p", "Choose two to four connections. Each receives identical evidence, without other models' answers.", "small muted"));
      for (const p of S.profiles) { const label = node("label", undefined, "desk-check"), input = node("input"); input.type = "checkbox"; input.value = p.id; input.checked = selected.has(p.id); input.addEventListener("change", invalidate); label.append(input, node("span", p.name + " / " + p.model)); $("desk-compare").append(label); }
      return;
    }
    for (const role of roles[mode]) {
      const label = node("label", role), select = node("select"); select.id = "desk-role-" + role; label.htmlFor = select.id; select.dataset.role = role;
      selectOptions(select, S.profiles, S.profiles.length ? undefined : "Connect a model first");
      select.value = saved[role] || prior[role] || S.profiles[0]?.id || "";
      select.addEventListener("change", invalidate); $("desk-routing").append(label, select);
    }
  }
  function configuration() {
    const current = W.current(); if (!current) throw new Error("Load a frozen scenario first.");
    return { run_id: current.result.run.run_id, question: $("desk-question").value.trim(), mode: $("desk-mode").value,
      role_profiles: Object.fromEntries([...$("desk-routing").querySelectorAll("select")].map(e => [e.dataset.role, e.value])),
      compare_profiles: [...$("desk-compare").querySelectorAll("input:checked")].map(e => e.value),
      max_tokens: Number($("desk-tokens").value), max_calls: Number($("desk-calls").value), max_cost_usd: nullable("desk-cap") };
  }
  async function preview(extra = {}) {
    invalidate(); const p = await W.api("research_session", { action: "plan", body: { ...configuration(), ...extra } }); S.plan = p;
    const box = $("desk-preview-result"); box.replaceChildren(node("strong", "Review before sending"), node("p", p.question));
    box.append(node("p", `Frozen ${p.context.cutoff} · ${p.context.inspect_evidence.length} evidence inputs · ${p.context.excluded_evidence_ids.length} excluded`, "small"));
    for (const r of p.routes) box.append(node("p", `${r.role}: ${r.profile.name} / ${r.profile.model} → ${r.profile.base_url}`, "small"));
    box.append(node("p", `At most ${p.max_calls} calls · ${p.max_tokens} requested output tokens per call · reservation ${money(p.reserved_cost_usd)}`, "small"));
    const details = node("details"), summary = node("summary", "Inspect the frozen data sent to these models"); details.append(summary, node("pre", JSON.stringify(p.context, null, 2))); box.append(details);
    box.append(node("p", "API usage may be billable. The context contains the loaded receipt's eligible evidence and dated memory, never its synthetic settlement. Model training cutoffs are unverified.", "small"));
    box.hidden = false; $("desk-start").hidden = false; message("desk-status", "Preview ready. Start sends this context to the listed destinations.");
    document.dispatchEvent(new CustomEvent("tradefloor:plan-previewed", { detail: p }));
  }
  function profileForm(p) {
    $("profile-edit").value = p?.id || ""; $("profile-key").value = "";
    for (const [key, id] of Object.entries({ name:"profile-name", protocol:"profile-protocol", model:"profile-model", base_url:"profile-url", key_env:"profile-env", token_parameter:"profile-token-param", input_price:"profile-input-price", output_price:"profile-output-price" })) $(id).value = p?.[key] ?? (key === "protocol" ? "openai" : key === "token_parameter" ? "max_tokens" : "");
    $("profile-stream-usage").checked = p?.stream_usage || false;
    $("profile-test").disabled = !p; $("profile-delete").disabled = !p;
    message("profile-status", p ? `Editing ${p.name}. ${p.has_key ? "A key is stored in the OS credential store." : p.key_env ? "Uses server environment " + p.key_env + "." : "No key stored."}` : "Create a connection, then test it before starting research.");
  }
  async function refreshProfiles() {
    const data = await W.api("model_profile"); S.profiles = data.profiles;
    selectOptions($("profile-edit"), S.profiles, "New connection");
    $("profile-vault").textContent = data.credential_store_available ? "OS credential store available." : "OS credential store unavailable. Set the key in a server environment variable and enter its name below.";
    $("profile-list").replaceChildren();
    for (const p of S.profiles) {
      const line = node("div", undefined, "desk-profile"); line.append(node("strong", p.name), node("p", p.model), node("p", p.base_url, "small muted"), node("p", `${p.protocol} · ${p.has_key ? "OS key" : p.key_env ? "Environment key" : "No key"} · supplied prices ${money(p.input_price)} / ${money(p.output_price)} per million`, "small muted"));
      const edit = node("button", "Edit connection", "secondary"); edit.addEventListener("click", () => profileForm(p)); line.append(edit); $("profile-list").append(line);
    }
    if (!S.profiles.length) $("profile-list").append(node("p", "No connections configured. Local Ollama and LM Studio can work without a cloud key.", "muted"));
    routing(); invalidate(); message("desk-status", S.profiles.length ? "Choose your roles and preview the loaded receipt." : "Start in Models & keys to connect your chosen model.");
  }
  async function refreshRecipes() { const data = await W.api("research_recipe"); S.recipes = data.recipes; selectOptions($("desk-recipe"), S.recipes, "Choose a recipe"); }
  async function refreshSessions() { const data = await W.api("research_session"); S.sessions = data.sessions; selectOptions($("desk-session-select"), data.sessions.map(s => ({...s,name:s.question.slice(0,65) + " / " + s.state})), "Choose a session"); if(S.session && data.sessions.some(s=>s.id===S.session.id))$("desk-session-select").value=S.session.id; }
  function sessionMeta(s) { if(!s)return;const different=W.current()?.result.run.run_id!==s.plan.run_id;$("desk-session-meta").textContent=`${s.plan.mode} / ${s.plan.context.symbol} / frozen ${s.plan.context.cutoff} / receipt ${s.plan.run_id.slice(0,8)}${different?". This session uses a different receipt from the loaded chart.":"."}`; }
  async function refreshDatasets() { const data = await W.api("research_dataset"); S.datasets = data.datasets; selectOptions($("dataset-select"), S.datasets, "Choose a dataset"); }
  function renderSession(s) {
    document.dispatchEvent(new CustomEvent("tradefloor:session-loaded", { detail: s }));
    if (S.plan && S.plan.id !== s.id) invalidate();
    S.session = s; sessionMeta(s); $("desk-state").textContent = s.state.toUpperCase();
    if ([...$("desk-session-select").options].some(o=>o.value===s.id))$("desk-session-select").value=s.id;
    const running = ["queued", "running"].includes(s.state);
    $("desk-cancel").hidden = !running || s.imported; $("desk-export").disabled = running || s.imported; $("desk-follow").disabled = running || s.imported; $("desk-freeze").disabled = s.state !== "completed" || s.imported;
    $("desk-preview").disabled = running; $("desk-start").disabled = running;
    $("desk-activity").replaceChildren();
    for (const e of s.events || []) {
      const line = node("div", undefined, "desk-log"); line.append(node("strong", e.kind.replaceAll("_", " ") + (e.body.role ? " / " + e.body.role : "")));
      if (e.kind === "stream") { const detail = node("details"); detail.append(node("summary", "Inspect streamed response"), node("pre", e.body.text)); line.append(detail); }
      if (e.kind === "model_call") line.append(node("p", `${e.body.model} · call ${e.body.call}`, "small"));
      if (e.kind === "tool_result") { line.append(node("p", e.body.tools.join(", "), "small")); const d = node("details"); d.append(node("summary", "Read tool receipt"), node("pre", JSON.stringify(e.body.results, null, 2))); line.append(d); }
      if (e.body.error) line.append(node("p", e.body.error, "small")); $("desk-activity").append(line);
    }
    if (!s.events?.length) $("desk-activity").append(node("p", "Queued. The local research worker will process this session.", "muted"));
    const reported = s.usage.filter(x => x.calculated_cost_usd !== null), cost = reported.reduce((n,x)=>n+x.calculated_cost_usd,0);
    $("desk-usage").replaceChildren(node("p", `${s.calls} calls · calculated cost ${money(cost)}${reported.length < s.calls ? " + unknown usage" : ""} · supplied rates`, "desk-usage"));
    $("desk-responses").replaceChildren();
    for (const r of s.responses) {
      const card = node("article", undefined, "card desk-response"), header = node("header"); header.append(node("h3", r.role), node("span", r.profile.name + " / " + r.profile.model, "small muted")); card.append(header);
      if (r.error) { card.append(node("p", r.error)); $("desk-responses").append(card); continue; }
      card.append(node("p", r.output.summary));
      if (r.output.abstain) card.append(node("strong", "ABSTAINED"));
      const forecast = r.audit.forecast;
      if (forecast) { const probs = node("div", undefined, "desk-probabilities"); for (const k of ["down","flat","up"]) probs.append(node("span", k.toUpperCase() + " " + pct(forecast.probabilities[k]))); card.append(probs);
        const d = node("details"), rows = node("div"); d.append(node("summary", "Inspect every probability adjustment"));
        for (const a of r.output.adjustments || []) rows.append(node("p", `${a.class}: ${(100*a.delta).toFixed(2)} points · ${a.reason} · ${(a.evidence_ids || []).join(", ")}`, "small"));
        if (!rows.children.length) rows.append(node("p", "No adjustment from the numerical prior.", "small")); d.append(rows); card.append(d);
      }
      if (r.audit.probability_error) card.append(node("p", r.audit.probability_error, "review"));
      for (const claim of r.audit.claims) {
        const row = node("div", undefined, "desk-claim"); row.append(node("p", claim.text), node("p", claim.status, "small" + (claim.flags.length ? " review" : " muted")));
        for (const id of claim.evidence_ids.filter(x => typeof x === "string")) {
          const button = node("button", id, "secondary desk-source"); button.addEventListener("click", () => { const evidence = s.plan.context.inspect_evidence.find(n=>n.id===id); if (evidence) { row.append(node("p", evidence.text, "small muted")); button.disabled=true; } }); row.append(button);
        }
        for (const flag of claim.flags) row.append(node("p", flag, "small review")); card.append(row);
      }
      if (r.audit.issues.length) card.append(node("p", `${r.audit.issues.length} review flags. Read the structured claims before relying on this answer.`, "small"));
      card.append(node("p", r.audit.note, "small muted")); $("desk-responses").append(card);
    }
    renderDisagreements(s); if (s.error) message("desk-status", s.error, true);
    else message("desk-status", s.imported ? s.trust : s.state === "cancelled" ? "Session cancelled. Partial output is preserved; in-flight usage may still be billed." : running ? "Research is running on the previewed frozen context." : "Session preserved. References were checked; model judgments still require review.");
  }
  function renderDisagreements(s) {
    const box = $("desk-disagreements"); box.replaceChildren();
    for (const d of s.disagreements || []) box.append(node("p", `${d.left} / ${d.right}: ${d.direction_disagrees ? "different directions" : "same direction"}; largest class gap ${(100*d.largest_probability_gap).toFixed(1)} points.`, "small"));
    for (const r of s.responses.filter(r=>r.output)) {
      for (const key of ["assumptions","objections"]) for (const entry of r.output[key] || []) box.append(node("p", `${r.role} / ${key}: ${typeof entry === "string" ? entry : JSON.stringify(entry)}`, "small"));
      for (const resolution of r.output.resolutions || []) { const row=node("div",undefined,"desk-resolve"); if (resolution && typeof resolution === "object") row.append(node("strong", resolution.question || "Missing observation"),node("p","Evidence needed: " + (resolution.evidence_needed || "Unspecified")),node("p","Test: " + (resolution.test || "Unspecified"),"small muted")); else row.append(node("p",String(resolution))); box.append(row); }
    }
    if (!box.children.length) box.append(node("p", "No comparable validated forecasts yet. Failures and abstentions remain in the transcript.", "muted"));
    else box.append(node("p", "Observations and tests above are model proposals. They are not automatically executed or proven to resolve the disagreement.", "small muted"));
  }
  async function poll(id, generation) {
    if (generation === undefined) generation = ++S.pollGeneration;
    clearTimeout(S.timer);
    try { const s = await W.api("research_session", { action:"get",session_id:id }); if(generation!==S.pollGeneration)return; renderSession(s); if (["queued","running"].includes(s.state)) S.timer=setTimeout(()=>poll(id,generation),1000); else await refreshSessions(); }
    catch(e) { message("desk-status",e.message,true); }
  }
  function download(value, name) { const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:"application/json"})), a=node("a"); a.href=url; a.download=name; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000); }
  $("desk-connect").addEventListener("click",()=>W.tab("connections"));
  $("desk-mode").addEventListener("change",()=>{ routing(); $("desk-calls").value = $("desk-mode").value === "compare" ? 8 : 2 * roles[$("desk-mode").value].length; invalidate(); });
  for (const id of ["desk-question","desk-tokens","desk-calls","desk-cap"]) $(id).addEventListener("input",invalidate);
  $("desk-preview").addEventListener("click",()=>action("desk-status",()=>preview()));
  $("desk-start").addEventListener("click",()=>action("desk-status",async()=>{ if (!S.plan) throw new Error("Preview the context first."); const r=await W.api("research_session",{action:"start",body:{plan_id:S.plan.id,plan_sha256:S.plan.sha256}}); $("desk-start").hidden=true; await poll(r.session_id); }));
  $("desk-cancel").addEventListener("click",()=>action("desk-status",async()=>{ if (S.session) { await W.api("research_session",{action:"cancel",session_id:S.session.id}); await poll(S.session.id); } }));
  $("desk-refresh").addEventListener("click",()=>action("desk-status",refreshSessions));
  $("desk-session-select").addEventListener("change",()=>action("desk-status",async()=>{const id=$("desk-session-select").value;if(!id)return;clearTimeout(S.timer);++S.pollGeneration;const s=await W.api("research_session",{action:"get",session_id:id});if(!s.imported){W.render(await W.api("load_run",{run_id:s.plan.run_id}));$("desk-mode").value=s.plan.mode;$("desk-question").value=s.plan.question;$("desk-calls").value=s.plan.max_calls;$("desk-tokens").value=s.plan.max_tokens;$("desk-cap").value=s.plan.max_cost_usd??"";routing(Object.fromEntries(s.plan.routes.map(r=>[r.role,r.profile.id])));for(const e of $("desk-compare").querySelectorAll("input"))e.checked=s.plan.routes.some(r=>r.profile.id===e.value);}await poll(id);}));
  $("desk-export").addEventListener("click",()=>action("desk-status",async()=>{ const r=await W.api("research_session",{action:"export",session_id:S.session.id}); download(r,"tradefloor-session-"+S.session.id+".json"); message("desk-status","Exported the full session, including its private evidence. Credentials are excluded."); }));
  $("desk-import").addEventListener("click",()=>$("desk-archive-file").click());
  $("desk-archive-file").addEventListener("change",()=>action("desk-status",async()=>{ const file=$("desk-archive-file").files[0]; if(!file)return; if(file.size>20000000)throw new Error("Session archive exceeds 20 MB."); const imported=await W.api("session_archive",{payload:JSON.parse(await file.text())}); $("desk-import-result").replaceChildren(node("p",imported.trust),node("p",`${imported.recomputed_audits.length} response audits recomputed. Imported sessions are preserved as data and never executed.`)); renderSession(await W.api("research_session",{action:"get",session_id:imported.id})); await refreshSessions(); $("desk-archive-file").value=""; }));
  $("desk-follow").addEventListener("click",()=>action("desk-status",async()=>{ if(!S.session)throw new Error("Open a saved session first."); const r=await W.api("load_run",{run_id:S.session.plan.run_id}); W.render(r); $("desk-mode").value="chat"; routing({researcher:S.session.plan.routes[0].profile.id}); $("desk-question").value=$("desk-follow-question").value; $("desk-calls").value=2; await preview({parent_id:S.session.id}); }));
  $("desk-save-recipe").addEventListener("click",()=>action("desk-status",async()=>{ await W.api("research_recipe",{action:"save",body:{...configuration(),name:$("desk-recipe-name").value}}); await refreshRecipes(); message("desk-status","Recipe saved. It will not make automatic provider calls."); }));
  $("desk-recipe").addEventListener("change",()=>{const r=S.recipes.find(r=>r.id===$("desk-recipe").value); if(!r)return; $("desk-mode").value=r.mode; $("desk-question").value=r.question; $("desk-tokens").value=r.max_tokens; $("desk-calls").value=r.max_calls; $("desk-cap").value=r.max_cost_usd??""; routing(r.role_profiles); for(const e of $("desk-compare").querySelectorAll("input"))e.checked=(r.compare_profiles||[]).includes(e.value); invalidate(); });
  $("profile-edit").addEventListener("change",()=>profileForm(S.profiles.find(p=>p.id===$("profile-edit").value)));
  $("profile-preset").addEventListener("change",()=>{const presets={openai:["openai","https://api.openai.com/v1"],anthropic:["anthropic","https://api.anthropic.com/v1"],ollama:["openai","http://localhost:11434/v1"],lmstudio:["openai","http://localhost:1234/v1"],openrouter:["openai","https://openrouter.ai/api/v1"]}; const p=presets[$("profile-preset").value]; if(p){$("profile-protocol").value=p[0];$("profile-url").value=p[1];} });
  $("profile-form").addEventListener("submit",event=>{event.preventDefault();action("profile-status",async()=>{ const body={name:$("profile-name").value,protocol:$("profile-protocol").value,base_url:$("profile-url").value,model:$("profile-model").value,key_env:$("profile-env").value.trim(),input_price:nullable("profile-input-price"),output_price:nullable("profile-output-price"),token_parameter:$("profile-token-param").value,stream_usage:$("profile-stream-usage").checked}; const args={action:"save",profile_id:$("profile-edit").value||null,body}; if($("profile-key").value)args.api_key=$("profile-key").value; try {const p=await W.api("model_profile",args); await refreshProfiles(); profileForm(p); message("profile-status","Connection saved. Test makes one potentially billable call.");} finally{$("profile-key").value="";} });});
  $("profile-test").addEventListener("click",()=>action("profile-status",async()=>{message("profile-status","Testing the saved connection…"); const r=await W.api("model_profile",{action:"test",profile_id:$("profile-edit").value}); message("profile-status",`Connected in ${r.latency_ms.toFixed(0)} ms. Reported usage: ${JSON.stringify(r.usage)}.`); }));
  $("profile-delete").addEventListener("click",()=>action("profile-status",async()=>{await W.api("model_profile",{action:"delete",profile_id:$("profile-edit").value}); await refreshProfiles();profileForm(null);message("profile-status","Connection and its stored credential removed. Existing research receipts retain model provenance.");}));
  $("desk-freeze").addEventListener("click",()=>action("desk-status",async()=>{const r=await W.api("forecast_commitment",{action:"freeze",session_id:S.session.id,body:{settlement_at:utc("desk-settlement"),settlement_rule:$("desk-rule").value}}); $("desk-scores-result").replaceChildren(node("p",`Frozen ${r.predictions.length} forecasts. Commitment ${r.sha256}. ${r.publication_status}`));}));
  $("desk-settle").addEventListener("click",()=>action("desk-status",async()=>{if(!S.session)throw new Error("Open the committed session first.");await W.api("forecast_commitment",{action:"settle",session_id:S.session.id,body:{outcome:$("desk-outcome").value,available_at:utc("desk-available"),source:$("desk-outcome-source").value}});await scores();}));
  async function scores(){const r=await W.api("forecast_commitment"); const box=$("desk-scores-result");box.replaceChildren();for(const c of r.commitments)box.append(node("p",`${c.id} · ${c.synthetic?"synthetic":"supplied history"} · settles ${c.settlement_at} · ${c.publication_status}`,"small")); for(const o of r.outcomes){box.append(node("p",`${o.outcome} · ${o.verification}`,"small"));for(const score of o.scores)box.append(node("p",`${score.role} / ${score.model}: Brier ${score.brier_multiclass.toFixed(4)} · log loss ${score.log_loss.toFixed(4)}`,"small"));}if(!box.children.length)box.append(node("p","No commitments or matured outcomes recorded.","muted"));box.append(node("p",`${r.evaluation.failed_sessions} failed sessions / ${r.evaluation.cancelled_sessions} cancelled / ${r.evaluation.abstentions} abstentions`,"small"));for(const m of r.evaluation.models)box.append(node("p",`${m.connection_name || 'Legacy connection'} / ${m.model} / ${m.synthetic?"synthetic":"supplied history"}: ${m.session_count} events, ${m.forecast_count} forecasts / mean Brier ${m.brier_multiclass.toFixed(4)} / log loss ${m.log_loss.toFixed(4)}`,"small"));const detail=node("details");detail.append(node("summary","Inspect reliability bins"),node("pre",JSON.stringify(r.evaluation.models.map(m=>({model:m.model,connection_name:m.connection_name,model_key:m.model_key,synthetic:m.synthetic,reliability:m.reliability})),null,2)));box.append(detail,node("p",r.evaluation.note,"small muted"));}
  $("desk-scores").addEventListener("click",()=>action("desk-status",scores));
  $("dataset-csv-file").addEventListener("change",()=>action("dataset-status",async()=>{const f=$("dataset-csv-file").files[0];if(!f)return;if(f.size>2000000)throw new Error("CSV exceeds 2 MB.");$("dataset-csv").value=await f.text();}));
  $("dataset-form").addEventListener("submit",event=>{event.preventDefault();action("dataset-status",async()=>{const r=await W.api("research_dataset",{action:"import",body:{name:$("dataset-name").value,symbol:$("dataset-symbol").value,source:$("dataset-source").value,available_at:utc("dataset-time"),adjustment_basis:$("dataset-basis").value,rights:$("dataset-rights").value,csv:$("dataset-csv").value}});await refreshDatasets();$("dataset-select").value=r.id;datasetDetails();message("dataset-status",`Imported ${r.rows} daily rows with a preserved source hash.`);});});
  function datasetDetails(){const d=S.datasets.find(d=>d.id===$("dataset-select").value);$("dataset-details").replaceChildren();if(d)$("dataset-details").append(node("p",`${d.symbol} · ${d.rows} rows · last price ${d.last_date}`,"small"),node("p",d.source,"small muted"),node("p","Availability: "+d.available_at,"small muted"));}
  $("dataset-select").addEventListener("change",datasetDetails);
  $("source-settings-form").addEventListener("submit",event=>{event.preventDefault();action("dataset-status",async()=>{const args={action:"save",body:{sec_contact:$("source-sec-contact").value,key_env:$("source-fred-env").value.trim()}};if($("source-fred-key").value)args.api_key=$("source-fred-key").value;try{const r=await W.api("data_source_settings",args);$("source-settings-state").textContent=r.note;message("dataset-status","Dated-source settings saved. Fetch a chosen source from Information timeline.");}finally{$("source-fred-key").value="";}});});
  $("dataset-open").addEventListener("click",()=>action("dataset-status",async()=>{const r=await W.api("research_dataset",{action:"scenario",dataset_id:$("dataset-select").value,body:{case:$("case").value,hypothesis:$("dataset-hypothesis").value}});W.render(r);W.tab("thesis");W.status("Opened a scenario on supplied daily history. Event reactions remain explicit assumptions.");}));
  $("dataset-capture").addEventListener("click",()=>action("dataset-status",async()=>{const j=await W.api("research_job",{action:"submit",kind:"dataset_capture",arguments:{name:$("capture-name").value,symbol:$("capture-symbol").value},idempotency_key:crypto.randomUUID()});message("dataset-status","Provider capture queued. Its availability is the capture time.");const check=async()=>{try{const job=await W.api("research_job",{action:"get",job_id:j.id});if(["queued","running"].includes(job.state))setTimeout(check,1500);else if(job.state==="completed"){await refreshDatasets();message("dataset-status","History captured. Current adjusted history is not a historical vintage.");}else message("dataset-status",job.error||job.state,true);}catch(e){message("dataset-status",e.message,true);}};await check();}));
  async function init() {
    if (S.ready) return; S.ready=true; S.initializing=true; $("desk-preview").disabled=true;
    if(W.offline){S.initializing=false;$("desk-notice").textContent="Model research, connections and datasets require the local workspace. This standalone page contains frozen synthetic examples only.";for(const view of ["desk","connections","data"])for(const e of $("view-"+view).querySelectorAll("input,select,textarea,button"))if(!e.closest(".research-map"))e.disabled=true;return;}
    try{await refreshProfiles();await refreshRecipes();await refreshSessions();await refreshDatasets();const sources=await W.api("data_source_settings");$("source-sec-contact").value=sources.sec_contact;$("source-fred-env").value=sources.key_env;$("source-settings-state").textContent=sources.has_key?"An ALFRED key is stored in the OS credential store.":sources.note;message("desk-status",S.profiles.length?"Choose your roles and preview the loaded receipt.":"Start in Models & keys to connect your chosen model.");}catch(e){S.ready=false;message("desk-status",e.message,true);}finally{S.initializing=false;$("desk-preview").disabled=!S.ready||["queued","running"].includes(S.session?.state);}
  }
  document.addEventListener("tradefloor:run-loaded",()=>{invalidate();sessionMeta(S.session);init();});
  if(W.current()||W.offline)init();
})();
