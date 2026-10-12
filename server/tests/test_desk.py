"""Provider transport and research invariants without credentials or external network."""
import copy
import json
import threading
import time
from datetime import datetime, timedelta, timezone

import httpx
import pandas as pd
import pytest

from tradefloor import datahub, demo, desk, jobs, lab, providers, research, runs


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADEFLOOR_HOME", str(tmp_path))


@pytest.fixture
def source():
    return lab.simulate(worlds=100, sensitivity=False)["run"]["run_id"]


def profile(**kwargs):
    return providers.profiles("save", body={"name": "Local model", "protocol": "openai", "base_url": "http://127.0.0.1:1234/v1", "model": "fixture-model", **kwargs})


def response(context):
    return {"summary": "The cited assumption needs testing.", "claims": [{"id": "C1", "text": "The event is an assumption.", "evidence_ids": ["E1"], "quotes": [{"evidence_id": "E1", "text": context["inspect_evidence"][0]["text"]}]}],
            "probabilities": context["baseline_forecasts"]["quant"], "adjustments": [], "abstain": False,
            "assumptions": ["Reaction persistence is supplied"], "objections": ["The event may be priced in"],
            "resolutions": [{"question": "Does attention persist?", "evidence_needed": "Dated flow observations", "test": "Compare persistence assumptions"}]}


def started(source, **settings):
    p = profile()
    plan = desk.session("plan", body={"run_id": source, "profile_id": p["id"], "question": "What changes this thesis?", "mode": "quick", **settings})
    handle = desk.session("start", body={"plan_id": plan["id"], "plan_sha256": plan["sha256"]})
    return plan, handle


@pytest.mark.parametrize("url", ["http://example.com/v1", "https://user:pass@example.com/v1", "https://example.com/v1?key=secret", "https://169.254.169.254/v1", "https://10.0.0.1/v1"])
def test_rejects_unsafe_endpoint_forms(url):
    with pytest.raises(ValueError):
        profile(base_url=url)


def test_secrets_use_vault_and_never_database(monkeypatch):
    class Vault:
        values = {}
        def set_password(self, service, name, value): self.values[(service, name)] = value
        def get_password(self, service, name): return self.values.get((service, name))
        def delete_password(self, service, name): self.values.pop((service, name))
    vault = Vault()
    monkeypatch.setattr(providers, "_vault", lambda: vault)
    p = providers.profiles("save", body={"name": "Private", "base_url": "https://example.com/v1", "model": "m"}, api_key="secret-test-credential")
    assert providers._secret(p) == "secret-test-credential"
    assert "secret-test-credential" not in research.database().read_bytes().decode("latin1")
    assert "secret-test-credential" not in json.dumps(providers.profiles())
    with pytest.raises(ValueError, match="Re-enter"):
        providers.profiles("save", p["id"], {"name": "Private", "base_url": "https://different.example/v1", "model": "m"})
    providers.profiles("delete", p["id"])
    assert not vault.values


def test_no_plaintext_vault_fallback(monkeypatch):
    monkeypatch.setattr(providers.keyring, "get_keyring", lambda: object())
    with pytest.raises(ValueError, match="environment"):
        providers.profiles("save", body={"name": "Key", "base_url": "https://example.com/v1", "model": "m"}, api_key="secret")


def test_failed_destination_rotation_retains_old_credential(monkeypatch):
    class Vault:
        values = {}
        def set_password(self, service, name, value): self.values[name] = value
        def get_password(self, service, name): return self.values.get(name)
        def delete_password(self, service, name): self.values.pop(name)
    vault = Vault()
    monkeypatch.setattr(providers, "_vault", lambda: vault)
    original = providers.profiles("save", body={"name": "Original", "base_url": "https://old.example/v1", "model": "m"}, api_key="original-secret")
    real_connect, calls = providers.connect, []
    def fail_write(path):
        calls.append(path)
        if len(calls) == 2:
            raise OSError("simulated metadata failure")
        return real_connect(path)
    monkeypatch.setattr(providers, "connect", fail_write)
    with pytest.raises(ValueError, match="previous connection"):
        providers.profiles("save", original["id"], {"name": "Replacement", "base_url": "https://new.example/v1", "model": "m"}, api_key="replacement-secret")
    monkeypatch.setattr(providers, "connect", real_connect)
    unchanged = providers.profiles("get", original["id"])
    assert unchanged["base_url"] == "https://old.example/v1"
    assert providers._secret(unchanged) == "original-secret"
    assert list(vault.values.values()) == ["original-secret"]


@pytest.mark.parametrize("protocol", ["openai", "anthropic"])
def test_stream_protocol_usage_and_secret_redaction(monkeypatch, protocol):
    monkeypatch.setenv("TEST_MODEL_KEY", "secret-credential")
    seen = []
    def transport(request):
        payload = json.loads(request.content)
        assert payload["stream"] and payload["model"] == "fixture-model"
        if protocol == "openai":
            assert request.headers["Authorization"] == "Bearer secret-credential"
            chunks = [{"choices": [{"delta": {"content": "secret-"}}]}, {"choices": [{"delta": {"content": "credential connected"}}]}, {"choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 3}}]
            lines = ["data: " + json.dumps(x) for x in chunks] + ["data: [DONE]"]
        else:
            assert request.headers["x-api-key"] == "secret-credential"
            chunks = [{"type": "message_start", "message": {"usage": {"input_tokens": 10}}}, {"type": "content_block_delta", "delta": {"text": "connected"}}, {"type": "message_delta", "usage": {"output_tokens": 3}}, {"type": "message_stop"}]
            lines = ["data: " + json.dumps(x) for x in chunks]
        return httpx.Response(200, text="\n\n".join(lines))
    actual_client = httpx.Client
    monkeypatch.setattr(providers.httpx, "Client", lambda **kwargs: actual_client(transport=httpx.MockTransport(transport), **kwargs))
    p = profile(protocol=protocol, key_env="TEST_MODEL_KEY")
    r = providers.complete(p, "System", "Test", 128, seen.append)
    assert "connected" in r["text"]
    assert "secret-credential" not in "".join(seen) + r["text"]
    assert r["usage"].get("input_tokens", r["usage"].get("prompt_tokens")) == 10


def test_provider_errors_omit_body_and_key(monkeypatch):
    actual = httpx.Client
    monkeypatch.setattr(providers.httpx, "Client", lambda **kwargs: actual(transport=httpx.MockTransport(lambda request: httpx.Response(401, text="secret-token internal URL")), **kwargs))
    with pytest.raises(ValueError, match="HTTP 401") as error:
        providers.complete(profile(), "System", "Prompt", 128)
    assert "secret-token" not in str(error.value)


def test_plan_freezes_no_future_outcome_or_keys(source):
    plan, handle = started(source)
    context = json.dumps(plan["context"])
    assert "demo_settlement" not in context and "synthetic_outcome" not in context and "actual_shock" not in context
    assert plan["reserved_cost_usd"] is None
    assert "key_env" not in json.dumps(plan["routes"])
    assert desk.session("start", body={"plan_id": plan["id"], "plan_sha256": plan["sha256"]}) == handle
    with pytest.raises(ValueError, match="Preview changed"):
        desk.session("start", body={"plan_id": plan["id"], "plan_sha256": "wrong"})


def test_unknown_prices_cannot_claim_cost_cap(source):
    with pytest.raises(ValueError, match="Cost cap"):
        started(source, max_cost_usd=1)


def test_full_session_tool_followup_audit_archive(source, monkeypatch):
    p, h = started(source)
    called = []
    def complete(profile, system, prompt, max_tokens, on_delta, cancelled):
        cancelled()
        payload = json.loads(prompt)
        called.append(payload)
        output = {"summary": "Read the evidence first", "tool_requests": ["inspect_evidence"]} if not payload.get("requested_tool_results") else response(payload["frozen_context"])
        raw = json.dumps(output)
        on_delta(raw)
        return {"text": raw, "usage": {"prompt_tokens": 20, "completion_tokens": 30}, "latency_ms": 12}
    monkeypatch.setattr(providers, "complete", complete)
    jobs.Worker().once()
    s = desk.session("get", h["session_id"])
    assert s["state"] == "completed" and s["calls"] == 4
    assert len(s["responses"]) == 2 and all(not r["audit"]["issues"] for r in s["responses"])
    assert len([e for e in s["events"] if e["kind"] == "tool_result"]) == 2
    assert "prior_role_outputs" in called[-1]
    exported = desk.session("export", s["id"])
    imported = desk.archive(exported)
    assert len(imported["recomputed_audits"]) == 2
    corrupted = json.loads(exported["archive_json"])
    corrupted["session"]["responses"][0]["output"]["summary"] = "edited"
    with pytest.raises(ValueError, match="hash"):
        desk.archive(corrupted)


def test_compare_models_never_receive_other_answers(source, monkeypatch):
    a, b = profile(), profile(name="Second")
    p = desk.plan({"run_id": source, "question": "Compare", "mode": "compare", "compare_profiles": [a["id"], b["id"]]})
    desk.session("start", body={"plan_id": p["id"], "plan_sha256": p["sha256"]})
    def complete(profile, system, prompt, *args):
        value = json.loads(prompt)
        assert "prior_role_outputs" not in value
        return {"text": json.dumps(response(value["frozen_context"])), "usage": {}, "latency_ms": 1}
    monkeypatch.setattr(providers, "complete", complete)
    jobs.Worker().once()
    s = desk.session("get", p["id"])
    assert len(s["disagreements"]) == 1


def test_cancel_preserves_partial_and_never_continues(source, monkeypatch):
    p, h = started(source)
    def complete(profile, system, prompt, max_tokens, on_delta, cancelled):
        on_delta("partial text")
        desk.session("cancel", h["session_id"])
        cancelled()
    monkeypatch.setattr(providers, "complete", complete)
    jobs.Worker().once()
    s = desk.session("get", h["session_id"])
    assert s["state"] == "cancelled" and s["calls"] == 1
    assert any(e["body"].get("text") == "partial text" for e in s["events"])
    desk.execute(s["id"])
    assert desk.session("get", s["id"])["calls"] == 1


def test_interrupted_billable_call_never_replays(source, monkeypatch):
    p, h = started(source)
    s = desk.session("get", h["session_id"])
    s.pop("events")
    s.update(state="running", calls=1)
    desk._put("desk-session:" + s["id"], s)
    monkeypatch.setattr(providers, "complete", lambda *args: pytest.fail("Must not replay provider request"))
    desk.execute(s["id"])
    assert desk.session("get", s["id"])["state"] == "failed"


def test_unknown_tool_and_invalid_json_retained_as_failures(source, monkeypatch):
    p, h = started(source)
    monkeypatch.setattr(providers, "complete", lambda *args: {"text": '{"summary":"execute","tool_requests":["shell"]}', "usage": {}, "latency_ms": 1})
    jobs.Worker().once()
    s = desk.session("get", h["session_id"])
    assert s["state"] == "failed" and len(s["responses"]) == 2
    assert not any(e["kind"] == "tool_result" for e in s["events"])


def test_audit_unknown_citations_quotes_numbers_and_probability_budget(source):
    _, context = desk._context(source)
    output = response(context)
    output["claims"] = [{"text": "Price 999", "evidence_ids": ["unknown"], "quotes": [{"evidence_id": "E1", "text": "invented quote"}], "numbers": [{"path": "event_contract.reference_price", "value": 999}]}]
    output["probabilities"] = {"up": 1, "down": 0, "flat": 0}
    checked = desk.audit(output, context)
    assert len(checked["issues"]) >= 4 and checked["forecast"] is None


def test_csv_provenance_and_supplied_scenario():
    dates = pd.bdate_range(end="2026-09-28", periods=900)
    raw = "Date,Close,High,Low\n" + "\n".join(f"{d.date()},{100 + i*.03 + (i%7)*.02},{101 + i*.03 + (i%7)*.02},{99 + i*.03 + (i%7)*.02}" for i, d in enumerate(dates))
    item = datahub.datasets("import", body={"name": "Fixture CSV", "symbol": "ACME", "csv": raw, "source": "User archive", "rights": "Research", "available_at": "2026-09-28T20:00:00Z"})
    assert item["rows"] == 900 and item["snapshot"]["rights"] == "Research"
    result = datahub.datasets("scenario", item["id"], {"hypothesis": "Attention increases"})
    assert "demo_settlement" not in result["result"]
    assert result["result"]["symbol"] == "ACME"
    receipt = runs.read(result["result"]["run"]["run_id"])
    assert receipt["inputs"]["prices"]["rights"] == "Research"
    fork = lab.fork(receipt["id"], {"sentiment": .2, "sensitivity": False})
    assert fork["symbol"] == "ACME"
    assert runs.read(fork["run"]["run_id"])["inputs"]["prices"]["rights"] == "Research"
    with pytest.raises(ValueError, match="252"):
        datahub.datasets("import", body={"name": "Tiny", "symbol": "X", "csv": "Date,Close\n2026-01-01,2", "source": "X", "rights": "X", "available_at": "2026-01-01T00:00:00Z"})


def test_commitment_cannot_backdate_or_settle_before_maturity(source, monkeypatch):
    p, h = started(source)
    monkeypatch.setattr(providers, "complete", lambda profile, system, prompt, *args: {"text": json.dumps(response(json.loads(prompt)["frozen_context"])), "usage": {}, "latency_ms": 1})
    jobs.Worker().once()
    with pytest.raises(ValueError, match="future"):
        desk.commitment("freeze", h["session_id"], {"settlement_at": "2026-01-01T00:00:00Z", "settlement_rule": "Receipt event"})
    future = datetime.now(timezone.utc) + timedelta(days=50)
    frozen = desk.commitment("freeze", h["session_id"], {"settlement_at": future.isoformat(), "settlement_rule": "Receipt event"})
    assert frozen["synthetic"] and len(frozen["predictions"]) == 2
    with pytest.raises(ValueError, match="matured"):
        desk.commitment("settle", h["session_id"], {"available_at": datetime.now(timezone.utc).isoformat(), "outcome": "UP", "source": "Observed"})
    with pytest.raises(ValueError, match="already frozen"):
        desk.commitment("freeze", h["session_id"], {"settlement_at": future.isoformat(), "settlement_rule": "Receipt event"})


def test_packaged_workspace_includes_all_new_panels():
    html = demo.workspace_document()
    assert "desk-start" in html and "profile-form" in html and "dataset-form" in html
    assert "/*DESK*/" not in html and "<!--DESK_PANELS-->" not in html


def test_browser_numeric_normalization_does_not_break_envelope(source, monkeypatch):
    p, h = started(source)
    monkeypatch.setattr(providers, "complete", lambda profile, system, prompt, *args: {"text": json.dumps(response(json.loads(prompt)["frozen_context"])), "usage": {}, "latency_ms": 1.0})
    jobs.Worker().once()
    archive = desk.session("export", h["session_id"])
    # Browser JSON.stringify turns 1.0 into 1; canonical archive bytes are a string.
    normalized = json.loads(json.dumps(archive), parse_float=lambda x: int(float(x)) if float(x).is_integer() else float(x))
    imported = desk.archive(normalized)
    reopened = desk.session("get", imported["id"])
    assert reopened["imported"] and reopened["state"] == "completed"
    assert any(s["id"] == imported["id"] for s in desk.session()["sessions"])


def test_forged_context_with_recomputed_hash_is_rejected(source, monkeypatch):
    p, h = started(source)
    monkeypatch.setattr(providers, "complete", lambda profile, system, prompt, *args: {"text": json.dumps(response(json.loads(prompt)["frozen_context"])), "usage": {}, "latency_ms": 1})
    jobs.Worker().once()
    b = json.loads(desk.session("export", h["session_id"])["archive_json"])
    b["session"]["plan"]["context"]["event_contract"]["reference_price"] = 999
    for obj in (b["session"]["plan"], b["session"], b):
        obj["sha256"] = runs.digest({k: v for k, v in obj.items() if k != "sha256"})
    with pytest.raises(ValueError, match="frozen source"):
        desk.archive(b)


def test_recipes_preserve_comparison_and_routes():
    a, b = profile(), profile(name="Other")
    recipe = desk.recipes("save", body={"name": "Compare", "question": "Compare this event", "mode": "compare", "compare_profiles": [a["id"], b["id"]]})
    assert desk.recipes("get", recipe["id"])["compare_profiles"] == [a["id"], b["id"]]


def test_memory_cannot_backdate_a_completed_model_session(source, monkeypatch):
    p, h = started(source)
    monkeypatch.setattr(providers, "complete", lambda profile, system, prompt, *args: {"text": json.dumps(response(json.loads(prompt)["frozen_context"])), "usage": {}, "latency_ms": 1})
    jobs.Worker().once()
    assert not desk.memory("2026-09-28T23:59:59Z")
    assert desk.memory((datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat())[0]["session_id"] == h["session_id"]


def test_matured_outcome_scores_and_correlation_disclosure(source, monkeypatch):
    p, h = started(source)
    monkeypatch.setattr(providers, "complete", lambda profile, system, prompt, *args: {"text": json.dumps(response(json.loads(prompt)["frozen_context"])), "usage": {}, "latency_ms": 1})
    jobs.Worker().once()
    now = datetime.now(timezone.utc)
    frozen = desk.commitment("freeze", h["session_id"], {"settlement_at": (now + timedelta(days=50)).isoformat(), "settlement_rule": "Receipt event"})
    monkeypatch.setattr(research, "now", lambda: (now + timedelta(days=52)).isoformat())
    outcome = desk.commitment("settle", h["session_id"], {"available_at": (now + timedelta(days=51)).isoformat(), "outcome": "UP", "source": "Supplied test receipt"})
    assert all(s["brier_multiclass"] >= 0 for s in outcome["scores"])
    summary = desk.commitment()["evaluation"]
    assert summary["models"][0]["session_count"] == 1 and summary["models"][0]["forecast_count"] == 2
    assert "correlated" in summary["note"]
    assert frozen["sha256"] == desk.commitment()["commitments"][0]["sha256"]
    with pytest.raises(ValueError, match="already recorded"):
        desk.commitment("settle", h["session_id"], {"available_at": (now + timedelta(days=51)).isoformat(), "outcome": "UP", "source": "Repeated"})


def test_saved_source_settings_do_not_fetch(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    monkeypatch.delenv("TRADEFLOOR_SEC_USER_AGENT", raising=False)
    monkeypatch.setenv("CUSTOM_FRED_KEY", "private-fred-key")
    saved = datahub.source_settings("save", {"sec_contact": "Test desk public@example.com", "key_env": "CUSTOM_FRED_KEY"})
    assert "private-fred-key" not in json.dumps(saved)
    assert datahub.source_credential("alfred") == "private-fred-key"
    assert datahub.source_credential("sec") == "Test desk public@example.com"


def test_provider_redirect_and_incomplete_stream_fail(monkeypatch):
    actual = httpx.Client
    monkeypatch.setattr(providers.httpx, "Client", lambda **kwargs: actual(transport=httpx.MockTransport(lambda request: httpx.Response(302, headers={"Location": "https://another.example"})), **kwargs))
    with pytest.raises(ValueError, match="302"):
        providers.complete(profile(), "System", "Prompt", 128)
    monkeypatch.setattr(providers.httpx, "Client", lambda **kwargs: actual(transport=httpx.MockTransport(lambda request: httpx.Response(200, text='data: {"choices":[{"delta":{"content":"partial"}}]}\n\n')), **kwargs))
    with pytest.raises(ValueError, match="complete"):
        providers.complete(profile(), "System", "Prompt", 128)


def test_http_profile_preview_start_and_worker(source, monkeypatch):
    monkeypatch.setattr(providers, "complete", lambda profile, system, prompt, *args: {"text": json.dumps(response(json.loads(prompt)["frozen_context"])), "usage": {}, "latency_ms": 1})
    server = demo.make_server(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with httpx.Client(trust_env=False) as client:
            def post(action, arguments):
                result = client.post(base + "/api/workspace", headers={"Origin": base}, json={"action": action, "arguments": arguments})
                result.raise_for_status()
                value = result.json()
                assert not value.get("error"), value
                return value
            denied = client.post(base + "/api/workspace", headers={"Origin": "https://foreign.example"}, json={"action": "model_profile"})
            assert denied.status_code == 403
            p = post("model_profile", {"action": "save", "body": {"name": "HTTP fixture", "base_url": "http://127.0.0.1:1234/v1", "model": "fixture"}})
            plan = post("research_session", {"action": "plan", "body": {"run_id": source, "profile_id": p["id"], "question": "Inspect evidence", "mode": "chat"}})
            started = post("research_session", {"action": "start", "body": {"plan_id": plan["id"], "plan_sha256": plan["sha256"]}})
            for _ in range(100):
                result = post("research_session", {"action": "get", "session_id": started["session_id"]})
                if result["state"] not in ("queued", "running"):
                    break
                time.sleep(.03)
            assert result["state"] == "completed" and result["responses"][0]["audit"]["forecast"]["valid"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize("updates", [
    {"assumptions": [{"toString": None}]},
    {"resolutions": ["do something"]},
    {"claims": [{"text": {"toString": None}}]},
    {"tool_requests": ["shell"]},
    {"abstain": "false"},
])
def test_malformed_model_responses_fail_cleanly(source, updates):
    _, context = desk._context(source)
    with pytest.raises(ValueError):
        desk.validate_response({**response(context), **updates})


def test_malformed_adjustments_cannot_crash_audit(source):
    _, context = desk._context(source)
    for adjustments in (["not an object"], [{"reason": {"toString": None}}]):
        checked = desk.audit({**response(context), "adjustments": adjustments}, context)
        assert checked["forecast"] is None and checked["probability_error"]


def test_same_model_alias_on_different_connections_is_not_merged():
    probabilities = {"up": .4, "down": .4, "flat": .2}
    scores = [{"model": "shared-alias", "model_key": k, "connection_name": k, "probabilities": probabilities, **desk.events.score(probabilities, "UP")} for k in ("provider-a", "provider-b")]
    result = desk.evaluation([], [{"id": "event-1", "synthetic": False, "outcome": "UP", "scores": scores}])
    assert len(result["models"]) == 2
    assert all(m["session_count"] == m["forecast_count"] == 1 for m in result["models"])


def test_corrupted_closed_memory_is_rejected(source, monkeypatch):
    p, h = started(source)
    monkeypatch.setattr(providers, "complete", lambda profile, system, prompt, *args: {"text": json.dumps(response(json.loads(prompt)["frozen_context"])), "usage": {}, "latency_ms": 1})
    jobs.Worker().once()
    value = desk._get("desk-session:" + h["session_id"])
    value["responses"][0]["output"]["summary"] = "Edited after sealing"
    desk._put("desk-session:" + h["session_id"], value)
    with pytest.raises(ValueError, match="integrity"):
        desk.memory((datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat())
