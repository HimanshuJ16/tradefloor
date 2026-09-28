import pandas as pd
import pytest

from tradefloor import journal, plan


def test_long_plan_math():
    p = plan.build_plan(price=100, atr=2, direction="UP", horizon_days=5, capital=100_000, risk_pct=1, max_position_pct=20)
    assert p["side"] == "long"
    assert p["stop_atr_multiple"] == 1.5
    assert p["stop"] == 97.0
    assert p["targets"][:2] == [104.5, 107.5]
    s = p["sizing"]
    # 1000 risk / 3 per unit = 333, but 20% cap = 200 units
    assert s["quantity"] == 200 and s["capped_by_max_position_pct"] is True
    assert s["loss_at_stop"] == 600.0


def test_lot_rounding():
    p = plan.build_plan(price=100, atr=2, direction="UP", horizon_days=5, capital=100_000, risk_pct=1, max_position_pct=100, lot_size=50)
    assert p["sizing"]["quantity"] == 300  # 333 rounded down to a multiple of 50


def test_bearish_without_short_is_reduce():
    p = plan.build_plan(price=100, atr=2, direction="DOWN", horizon_days=21)
    assert p["side"] == "reduce"


def test_short_plan():
    p = plan.build_plan(price=100, atr=2, direction="DOWN", horizon_days=5, allow_short=True)
    assert p["side"] == "short" and p["stop"] == 103.0 and p["targets"][0] == 95.5


def test_sideways_no_trade():
    assert plan.build_plan(price=100, atr=2, direction="SIDEWAYS", horizon_days=21)["side"] == "none"


def test_stop_multiple_caps():
    assert plan.stop_multiple(1) == 1.5
    assert plan.stop_multiple(252) == 4.0


def _bars(closes, lows=None, highs=None):
    idx = pd.bdate_range("2026-01-02", periods=len(closes))
    return pd.DataFrame({"Close": closes, "Low": lows or closes, "High": highs or closes}, index=idx)


def test_score_hit_and_brier():
    e = {"id": "a", "symbol": "X", "as_of": "2026-01-01", "horizon_days": 3, "price": 100, "direction": "UP", "p_up": 0.6, "p_down": 0.3, "stop": 95}
    r = journal.score_entry(e, _bars([101, 102, 104], lows=[99, 100, 101]))
    assert r["status"] == "scored" and r["hit"] is True and r["outcome"] == "UP"
    assert r["brier_up"] == pytest.approx(0.16)
    assert r["stop_hit"] is False


def test_score_open_when_horizon_not_elapsed():
    e = {"symbol": "X", "as_of": "2026-01-01", "horizon_days": 5, "price": 100, "direction": "UP", "p_up": 0.6, "p_down": 0.3}
    assert journal.score_entry(e, _bars([101, 102]))["status"] == "open"


def test_record_and_load(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADEFLOOR_HOME", str(tmp_path))
    journal.record({"symbol": "X", "as_of": "2026-01-01", "horizon_days": 5, "price": 100, "direction": "up", "p_up": 0.6, "p_down": 0.3})
    rows = journal.load()
    assert len(rows) == 1 and rows[0]["direction"] == "UP" and rows[0]["id"]
    with pytest.raises(ValueError):
        journal.record({"symbol": "X"})


def test_summary_needs_scored_calls():
    s = journal.summarize([{"status": "open"}], [])
    assert s["scored"] == 0
