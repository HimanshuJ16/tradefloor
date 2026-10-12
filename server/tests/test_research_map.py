"""Evidence withdrawal must preserve the numerical experiment and immutable parent."""
import pytest

from tradefloor import demo, desk, lab, runs


def test_withdrawal_branch_keeps_prices_assumptions_and_marks_dependents(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADEFLOOR_HOME", str(tmp_path))
    parent = lab.simulate(worlds=100, sensitivity=False)
    identifier = parent["run"]["run_id"]
    before = runs.read(identifier)
    child = demo.workspace_action({"action": "evidence_fork", "arguments": {"run_id": identifier, "evidence_id": "E1"}})
    bundle = runs.read(child["result"]["run"]["run_id"])
    assert bundle["parent"] == identifier
    assert runs.read(identifier) == before
    assert bundle["inputs"]["prices"] == before["inputs"]["prices"]
    for key in ("sentiment", "persistence", "retail_weight", "worlds", "seed"):
        assert bundle["request"][key] == before["request"][key]
    assert bundle["result"]["scenario"] == before["result"]["scenario"]
    graph = {n["id"]: n for n in bundle["result"]["evidence_graph"]["nodes"]}
    assert graph["E1"]["status"] == "retracted"
    assert graph["H1"]["status"] == "review required"
    _, context = desk._context(bundle["id"])
    assert "E1" in context["excluded_evidence_ids"]
    assert "E1" not in [n["id"] for n in context["inspect_evidence"]]
    with pytest.raises(ValueError, match="already retracted"):
        lab.fork_evidence(bundle["id"], "E1")
    for invalid in ("unknown", "H1", None, ["E1"]):
        with pytest.raises(ValueError, match="known evidence"):
            lab.fork_evidence(identifier, invalid)


def test_map_assets_are_inlined_for_offline_demo():
    html = demo.workspace_document()
    assert "TradefloorMapModel" in html
    assert 'id="map-svg"' in html
    assert "prefers-reduced-motion" in html
    assert "/*RESEARCH_MAP*/" not in html
