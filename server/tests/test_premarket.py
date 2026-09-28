from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from tradefloor import intraday as it
from tradefloor import journal
from tradefloor import premarket as pm
from test_intraday import make_bars

TZ = ZoneInfo("Asia/Kolkata")


def test_features_use_only_earlier_sessions():
    sess = it.sessions(make_bars(days=40, seed=3))
    table_full = pm.daily_table(sess)
    table_cut = pm.daily_table(sess[:30])
    a, b = pm.features_at(table_full, 30), pm.features_at(table_cut, 30)
    assert a == b  # sessions 30+ cannot change what was knowable before session 30
    assert pm.features_before(sess[:30])["session_date"] == sess[29].index[0].date()


def test_history_labels_each_session_from_its_own_bars():
    hist = {f"S{i}": it.sessions(make_bars(days=35, seed=i)) for i in range(3)}
    pool = pm.history(hist)
    assert len(pool) == 3 * (35 - pm.LOOKBACK - 1)
    assert set(pool.columns) >= {"value_ratio", "range_ratio", "big_move", "trend_day", "same_dir"}


def test_isotonic_is_monotone_and_weighted():
    out = pm.isotonic([0.1, 0.3, 0.2, 0.4], [10, 10, 30, 10])
    assert all(x <= y for x, y in zip(out, out[1:]))
    assert out[1] == pytest.approx((0.3 * 10 + 0.2 * 30) / 40)
    assert pm.isotonic([0.1, 0.2, 0.3], [1, 1, 1]) == [0.1, 0.2, 0.3]


def _session(rows):
    """rows of (high, low, close); 5-minute bars from 09:15."""
    idx = pd.date_range(datetime(2026, 7, 1, 9, 15, tzinfo=TZ), periods=len(rows), freq="5min")
    h, l, c = (np.array(x, dtype=float) for x in zip(*rows))
    return pd.DataFrame({"Open": c, "High": h, "Low": l, "Close": c, "Volume": 1.0}, index=idx)


OPENING = [(101, 99, 100)] * 3  # opening range 99 to 101, size 2


def test_orb_long_hits_target():
    r = pm.simulate_orb(_session(OPENING + [(101.5, 100.5, 101.2), (105.5, 101, 105)]), adr_abs=10)
    assert r["side"] == "LONG" and r["exit"] == "target" and r["r_multiple"] == 2.0


def test_orb_short_stopped():
    r = pm.simulate_orb(_session(OPENING + [(100, 98.5, 98.8), (101.5, 98.6, 101)]), adr_abs=10)
    assert r["side"] == "SHORT" and r["exit"] == "stop" and r["r_multiple"] == -1.0


def test_orb_skips_wide_range_and_respects_side():
    wide = [(106, 99, 100)] * 3 + [(107, 100, 106)]
    assert pm.simulate_orb(_session(wide), adr_abs=10)["status"] == "skipped"
    only_long = pm.simulate_orb(_session(OPENING + [(100, 98.5, 98.8)]), adr_abs=10, side="LONG")
    assert only_long["triggered"] is False


def test_orb_close_exit_in_r():
    r = pm.simulate_orb(_session(OPENING + [(101.5, 100.8, 101.4), (102, 101, 102)]), adr_abs=10)
    assert r["exit"] == "close" and r["r_multiple"] == pytest.approx(0.5)


def _pool(n_days, p_same, strong=True):
    rng = np.random.default_rng(0)
    rows = []
    for d in range(n_days):
        for s in range(20):
            rows.append({"date": d, "symbol": s, "value_ratio": 1.0, "range_ratio": 1.0, "strong_prev": strong,
                         "extreme_close": False, "same_dir": bool(rng.random() < p_same), "big_move": False, "trend_day": False})
    return pd.DataFrame(rows)


F = {"strong_prev": True, "prev_ret": 0.03, "prev_close_loc": 0.5}


def test_no_lean_within_two_standard_errors():
    assert pm.direction_lean(_pool(40, 0.45), F)["lean"] is None  # n_eff 120: 2 SE is about 0.09


def test_lean_when_it_clears_two_standard_errors():
    out = pm.direction_lean(_pool(40, 0.25), F)
    assert out["lean"] == "reversal" and out["side"] == "SHORT"


def test_no_lean_without_a_strong_day():
    assert pm.direction_lean(_pool(40, 0.25), {**F, "strong_prev": False})["lean"] is None


def test_orb_plan_sizes_from_typical_range():
    f = {"prev_close": 100.0, "prev_high": 102.0, "prev_low": 98.0, "adr_pct": 0.02, "typical_or": 0.8}
    p = pm.orb_plan(f, None, capital=100_000, risk_pct=0.5, max_position_pct=20, square_off="15:05")
    assert p["size_estimate"]["quantity"] == 200  # 500 / 0.8 = 625, capped at 20% = 200
    assert "either" in p["prefer"] and p["time_stop"] == "Square off by 15:05"


def test_premarket_journal_entry_validation(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADEFLOOR_HOME", str(tmp_path))
    base = {"kind": "intraday", "symbol": "X", "exchange": "NSE", "mode": "premarket", "direction": "EITHER"}
    with pytest.raises(ValueError):
        journal.record(base)  # no target_session, adr_pct, prev_close
    assert journal.record({**base, "target_session": "2026-09-28", "adr_pct": 0.02, "prev_close": 100, "p_big_move": 0.3})["id"]
