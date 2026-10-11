import copy
import json
from datetime import datetime, timezone, timedelta

import pytest

from tradefloor import (
    advanced,
    arena,
    evidence,
    intelligence,
    jobs,
    lab,
    research,
    runs,
    settings,
    timeline,
)
from tradefloor.storage import connect


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADEFLOOR_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def scenario():
    return lab.simulate(worlds=100, sensitivity=False)


def rehash(b):
    b["sha256"] = runs.digest({k: v for k, v in b.items() if k != "sha256"})
    return b


@pytest.mark.parametrize(
    "mutation",
    [
        lambda b: b["result"]["scenario"].update(p_up=2),
        lambda b: b["result"]["scenario"].update(fan=[]),
        lambda b: b["result"]["scenario"]["return_pct"].update(p10=900),
        lambda b: b["result"]["event_contract"].update(reference_price=1),
        lambda b: b["request"].update(worlds=999),
        lambda b: b.update(parent=b["id"]),
        lambda b: b.update(kind="arbitrary-code"),
        lambda b: b["result"]["evidence_graph"].update(edges=[]),
        lambda b: b["runtime"].update(source_sha256="not-a-hash"),
    ],
)
def test_valid_hash_cannot_bypass_semantic_validation(scenario, mutation):
    b = runs.read(scenario["run"]["run_id"])
    mutation(b)
    with pytest.raises(ValueError):
        runs.import_bundle(rehash(b))


def test_lineage_retraction_and_anchor():
    source = {
        "id": "E1",
        "kind": "source",
        "text": "Revenue rose.",
        "published_at": "2026-01-01T00:00:00Z",
        "available_at": "2026-01-01T00:00:00Z",
        "source_family": "release-1",
        "status": "retracted",
        "anchor": {"document_text": "Revenue rose.", "start": 0, "end": 13},
    }
    claims = [
        {"id": "H1", "text": "growth", "evidence_ids": ["E1"]},
        {
            "id": "H2",
            "text": "persistent",
            "evidence_ids": ["E1"],
            "depends_on": ["H1"],
        },
    ]
    g = evidence.graph(
        [source, {**source, "id": "E2", "text": "Revenue increased.", "anchor": None}],
        claims,
        "2026-02-01T00:00:00Z",
    )
    assert g["source_family_count"] == 1 and g["unique_text_count"] == 2
    assert "independent_evidence_count" not in g
    assert all(
        n["status"] == "review required"
        for n in g["nodes"]
        if n["kind"] == "interpretation"
    )
    claims[0]["depends_on"] = ["H2"]
    with pytest.raises(ValueError, match="cycle"):
        evidence.graph([source], claims, "2026-02-01T00:00:00Z")
    source["anchor"]["end"] = 12
    with pytest.raises(ValueError, match="anchor"):
        evidence.graph([source], [], "2026-02-01T00:00:00Z")


def test_project_conflict_export_import_preserves_lineage(scenario):
    root = scenario["run"]["run_id"]
    child = lab.fork(root, {"sentiment": -0.6})["run"]["run_id"]
    p = research.project("create", body={"title": "Earnings"})
    p = research.project("attach", p["id"], {"revision": 1, "run_id": child})
    with pytest.raises(ValueError, match="reload"):
        research.project("update", p["id"], {"revision": 1, "title": "stale"})
    assert len(research.project("history", p["id"])["revisions"]) == 2
    summary = research.export_project(p["id"])
    assert "bundles" not in summary and "evidence" not in summary
    payload = research.export_project(p["id"], True)
    assert len(payload["bundles"]) == 2
    imported = research.import_project(payload)
    assert imported["id"] != p["id"] and imported["runs"] == p["runs"]
    assert research.compare([root, child])["rows"][1]["changes"]
    bad = copy.deepcopy(payload)
    bad["bundles"] = bad["bundles"][:1]
    with pytest.raises(ValueError):
        research.import_project(bad)


def test_comparison_rejects_other_history(scenario):
    other = lab.simulate(case="policy", worlds=100, sensitivity=False)
    with pytest.raises(ValueError, match="event"):
        research.compare([scenario["run"]["run_id"], other["run"]["run_id"]])


def test_project_evidence_freezes_in_child_and_survives_fork(scenario):
    parent = runs.read(scenario["run"]["run_id"])
    sources = copy.deepcopy(parent["inputs"]["evidence"])
    sources[0]["status"] = "retracted"
    claims = [
        {"id": "H1", "text": "Review this thesis", "evidence_ids": [sources[0]["id"]]}
    ]
    p = research.project("create", body={"title": "Evidence review"})
    p = research.project(
        "update",
        p["id"],
        {
            "revision": p["revision"],
            "evidence": sources,
            "claims": claims,
            "cutoff": parent["result"]["evidence_graph"]["cutoff"],
        },
    )
    child = research.project_scenario(p["id"], parent["id"])
    frozen = runs.read(child["run"]["run_id"])
    assert frozen["parent"] == parent["id"]
    assert frozen["inputs"]["claims"] == claims
    assert child["scenario"] == scenario["scenario"]
    assert child["evidence_graph"]["nodes"][-1]["status"] == "review required"
    fork = lab.fork(frozen["id"], {"sentiment": -0.5})
    assert runs.read(fork["run"]["run_id"])["inputs"]["claims"] == claims
    forged = copy.deepcopy(frozen)
    forged["result"]["evidence_graph"]["nodes"][-1]["status"] = "active"
    with pytest.raises(ValueError, match="status"):
        runs.verify(rehash(forged))


def test_workspace_http_job_and_export(scenario):
    import threading
    import time
    from urllib.request import Request, urlopen
    from tradefloor import demo

    http = demo.make_server(0)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    root = f"http://127.0.0.1:{http.server_port}"

    def call(operation, **arguments):
        request = Request(
            root + "/api/workspace",
            data=json.dumps({"action": operation, "arguments": arguments}).encode(),
            headers={"Origin": root, "Content-Type": "application/json"},
        )
        with urlopen(request, timeout=10) as response:
            result = json.load(response)
        assert not result.get("error"), result
        return result

    try:
        project = call("research_project", action="create", body={"title": "HTTP test"})
        call(
            "research_project",
            action="attach",
            project_id=project["id"],
            body={"revision": project["revision"], "run_id": scenario["run"]["run_id"]},
        )
        archive = call("project_export", project_id=project["id"], include_data=True)
        assert len(archive["bundles"]) == 1
        job = call(
            "research_job",
            action="submit",
            kind="arena",
            idempotency_key="http-arena",
            arguments={"run_id": scenario["run"]["run_id"], "draws": 100},
        )
        deadline = time.monotonic() + 15
        while job["state"] in ("queued", "running") and time.monotonic() < deadline:
            time.sleep(0.05)
            job = call("job_result", job_id=job["id"])
        assert job["state"] == "completed", job
        assert len(job["result"]["forecasts"]) == 4
    finally:
        http.shutdown()
        http.server_close()
        thread.join()


def test_counterexample_budget_and_frozen_history(scenario):
    identifier = scenario["run"]["run_id"]
    challenge = research.challenge(
        identifier, {"sentiment": [-1, 1]}, points=3, budget=4
    )
    assert challenge["evaluated"] <= 4
    assert challenge["rows"][0]["distance"] == 0
    if challenge["run"]:
        comparison = research.compare([identifier, challenge["run"]["run_id"]])
        assert comparison["rows"][1]["randomness_pairing"].startswith("same seed")
    limited = research.challenge(identifier, budget=1)
    assert limited["counterexample"] is None and limited["guarantee"] == "none"


def vintage(value, available):
    return {
        "series": "CPI",
        "observation_key": "2026-01",
        "source": "fixture",
        "rights": "synthetic",
        "value": value,
        "effective_at": "2026-01-01T00:00:00Z",
        "published_at": available,
        "available_at": available,
        "retrieved_at": "2026-03-01T00:00:00Z",
    }


def test_timeline_later_revision_and_unknown_do_not_change_earlier_query():
    timeline.ingest([vintage(100, "2026-02-01T00:00:00Z")])
    before = timeline.query("2026-02-05T00:00:00Z")
    timeline.ingest([vintage(101, "2026-02-10T00:00:00Z"), vintage(999, None)])
    after = timeline.query("2026-02-05T00:00:00Z")
    assert before["snapshot_sha256"] == after["snapshot_sha256"]
    assert after["excluded"] == {"unknown_availability": 1, "later_availability": 1}
    assert timeline.query("2026-02-11T00:00:00Z")["records"][0]["value"] == 101


def test_archival_providers_bounded_and_credentials_hidden(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    with pytest.raises(ValueError, match="FRED_API_KEY"):
        timeline.fetch("alfred", "CPI", "2026-01-01")
    monkeypatch.setenv("TRADEFLOOR_SEC_USER_AGENT", "test contact@example.org")
    monkeypatch.setattr(
        timeline,
        "_fetch",
        lambda *a, **k: {
            "name": "Example",
            "filings": {
                "recent": {
                    "accessionNumber": ["001"],
                    "acceptanceDateTime": ["2026-01-01T10:00:00Z"],
                    "form": ["8-K"],
                    "primaryDocument": ["filing.htm"],
                    "filingDate": ["2026-01-01"],
                }
            },
        },
    )
    result = timeline.fetch("sec", "1")
    assert result["count"] == 1 and result["records"][0]["value"]["form"] == "8-K"
    with pytest.raises(ValueError):
        timeline.fetch("sec", "../etc")


def test_jobs_idempotency_failure_cancel_and_recovery(monkeypatch):
    job = jobs.submit("arena", {"run_id": "bad"}, "key")
    assert jobs.submit("arena", {"run_id": "bad"}, "key")["id"] == job["id"]
    with pytest.raises(ValueError, match="idempotency"):
        jobs.submit("arena", {}, "key")
    jobs.Worker().once()
    assert jobs.get(job["id"])["state"] == "failed"
    queued = jobs.submit("arena", {}, "cancel")
    assert jobs.cancel(queued["id"])["state"] == "cancelled"
    recover = jobs.submit("arena", {}, "recover")
    with connect(research.database()) as db:
        db.execute(
            "UPDATE jobs SET state='running',updated=0 WHERE id=?", (recover["id"],)
        )
    monkeypatch.setattr(jobs, "execute", lambda *a: {"ok": True})
    jobs.Worker().once()
    assert jobs.get(recover["id"])["result"] == {"ok": True}


def test_cli_job_with_null_error_is_success(capsys):
    from tradefloor import cli

    assert (
        cli.main(
            [
                "research_job",
                "--json",
                json.dumps(
                    {
                        "action": "submit",
                        "kind": "arena",
                        "arguments": {"run_id": "bad"},
                        "idempotency_key": "cli-job",
                    }
                ),
            ]
        )
        == 0
    )
    job = json.loads(capsys.readouterr().out)
    assert job["state"] == "queued" and job["error"] is None
    assert cli.main(["research_job", "action=work", "job_id=" + job["id"]]) == 1
    assert json.loads(capsys.readouterr().out)["state"] == "failed"


def test_arena_event_probabilities_and_external_mismatch(scenario):
    result = arena.forecast_run(scenario["run"]["run_id"], draws=100)
    assert len(result["forecasts"]) == 4
    assert all(
        sum(r["probabilities"].values()) == pytest.approx(1)
        for r in result["forecasts"]
    )
    bad = copy.deepcopy(result["forecasts"][0])
    bad["event_contract"]["flat_band"] += 0.1
    with pytest.raises(ValueError, match="mismatch"):
        arena.forecast_run(scenario["run"]["run_id"], external=[bad])


def test_block_evaluation_all_classes_and_insufficient_data():
    cases = [
        {
            "as_of": f"2026-01-{i:02}",
            "probabilities": {"up": 0.5, "down": 0.3, "flat": 0.2},
            "reference": {"up": 0.3, "down": 0.3, "flat": 0.4},
            "outcome": "UP",
        }
        for i in range(1, 21)
    ]
    r = arena.evaluate(cases, bootstrap_draws=200)
    assert set(r["reliability"]) == {"up", "down", "flat"}
    assert r["block_intervals_95"]["brier"][1] < 0
    assert arena.evaluate(cases[:2], bootstrap_draws=200)["block_intervals_95"] is None


def test_memory_cannot_backdate_and_outcomes_are_immutable():
    p = {
        "model_id": "test",
        "model_version": "1",
        "prompt_version": "1",
        "claim": "price direction",
        "context": "US",
        "phase": "independent",
        "as_of": "2026-01-01T00:00:00Z",
        "expires_at": "2026-01-02T00:00:00Z",
        "probabilities": {"up": 0.5, "down": 0.3, "flat": 0.2},
        "evidence_ids": [],
        "tool_receipts": [],
        "latency_ms": 10,
        "tokens": 20,
        "cost_usd": None,
    }
    assessment = intelligence.append("assessment", p)
    assert intelligence.memory("2026-01-03T00:00:00Z")["assessments"] == []
    outcome = {
        "assessment_id": assessment["id"],
        "outcome": "UP",
        "available_at": "2026-01-03T00:00:00Z",
    }
    intelligence.append("outcome", outcome)
    with pytest.raises(ValueError, match="already"):
        intelligence.append("outcome", outcome)
    future = (datetime.now(timezone.utc) + timedelta(seconds=5)).isoformat()
    assert len(intelligence.memory(future)["scores"]) == 1


def test_document_change_spans_and_financial_math():
    a, b = "Revenue 10\nMargin 2\n", "Revenue 12\nMargin 2\n"
    change = evidence.document_diff(a, b)["changes"][0]
    assert b[slice(*change["after_span"])] == change["after"]
    r = advanced.factor_stress(
        [{"symbol": "X", "value": 100, "currency": "USD", "loadings": {"rates": -2}}],
        {"rates": 0.01},
        "USD",
    )
    assert r["stress_pnl"] == -2
    weights = advanced.allocate([[0.04, 0], [0, 0.01]], 0.8)["weights"]
    assert weights == pytest.approx([0.2, 0.8], abs=1e-6)
    risk = advanced.option_implied(100, 0.2, 1, quote_as_of="2026-01-01T00:00:00Z")
    assert risk["atm_european_call"] == pytest.approx(7.965567, abs=1e-5)
    assert sum(risk["probabilities"].values()) == pytest.approx(1)
