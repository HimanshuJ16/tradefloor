from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from tradefloor import intraday as it
from tradefloor import journal

TZ = ZoneInfo("Asia/Kolkata")


def make_bars(days: int = 30, bars: int = 75, seed: int = 1, trend_last: float = 0.0) -> pd.DataFrame:
    """5-minute sessions 09:15-15:25 IST. trend_last adds a steady drift to the final session."""
    rng = np.random.default_rng(seed)
    frames, price = [], 100.0
    dates = pd.bdate_range("2026-07-01", periods=days)
    for i, d in enumerate(dates):
        idx = pd.date_range(datetime(d.year, d.month, d.day, 9, 15, tzinfo=TZ), periods=bars, freq="5min")
        drift = trend_last if i == days - 1 else 0.0
        steps = rng.normal(drift, 0.0015, bars)
        close = price * np.exp(np.cumsum(steps))
        open_ = np.concatenate([[price], close[:-1]])
        hi = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.0005, bars)))
        lo = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.0005, bars)))
        vol = rng.integers(1000, 3000, bars).astype(float)
        if i == days - 1 and trend_last:
            vol *= 3
        frames.append(pd.DataFrame({"Open": open_, "High": hi, "Low": lo, "Close": close, "Volume": vol}, index=idx))
        price = float(close[-1])
    return pd.concat(frames)


def test_sessions_split_by_date():
    s = it.sessions(make_bars(days=5))
    assert len(s) == 5 and all(len(x) == 75 for x in s)


def test_features_and_score_on_a_trend_day():
    sess = it.sessions(make_bars(trend_last=0.0008))
    f = it.features(sess[-1], 20, sess[:-1], bench_ret=0.0)
    d, sc, comp = it.score(f)
    assert d == 1 and sc > 0.3
    assert f["rvol"] > 2 and comp["rvol"] > 0.5 and f["price"] > f["vwap"]


def test_conflicting_signals_give_no_direction():
    f = {"price": 101, "vwap": 102, "ret_open": 0.01, "adr_pct": 0.02, "rvol": 2.0, "efficiency": 0.5,
         "orh": 102, "orl": 99, "rel_strength": 0.0}
    assert it.score(f)[0] == 0  # up since open but below VWAP


def test_truncate_at_is_point_in_time():
    df = make_bars(days=3)
    at = datetime(2026, 7, 3, 10, 30, tzinfo=TZ)
    cut = it.truncate_at(df, at)
    assert cut.index.max() + pd.Timedelta(minutes=5) <= at
    assert len(it.sessions(cut)[-1]) == 15  # 09:15..10:25 bars, all closed by 10:30


def test_calibration_uses_only_known_outcomes():
    hist = {f"S{i}": it.sessions(make_bars(seed=i)) for i in range(4)}
    cal = it.calibrate(hist, {}, lambda s: 12, "live", exclude_last=True)
    assert len(cal) > 0 and set(cal["outcome"]) <= {-1, 0, 1}
    last_day = hist["S0"][-1].index[0].date()
    assert last_day not in set(cal["date"])  # the current session's outcome is unknown


def test_probabilities_shrink_and_read():
    cal = pd.DataFrame({"abs_score": np.linspace(0, 1, 500), "outcome": [1, -1] * 250,
                        "fwd_adr": 0.0, "date": [d % 50 for d in range(500)]})
    p = it.probabilities(cal, 0.9)
    assert abs(p["p_follow"] + p["p_fade"] + p["p_flat"] - 1) < 0.01
    assert p["read"].startswith("no edge")
    assert it.probabilities(cal.head(10), 0.5)["p_follow"] is None


def test_live_plan_math():
    f = {"price": 100.0, "vwap": 99.5, "hod": 100.2, "lod": 98.0, "adr_pct": 0.02, "bar_range": 0.2,
         "prev_high": 101, "prev_low": 97}
    p = it.plan(f, 1, "live", capital=100_000, risk_pct=0.5, max_position_pct=20, square_off="15:05")
    assert p["trigger"] == 100.2 and p["risk_per_share"] == pytest.approx(0.7)  # trigger - vwap beats 1.5 x bar range
    assert p["stop"] == pytest.approx(99.5) and p["targets"] == [pytest.approx(100.9), pytest.approx(101.6)]
    assert p["size"]["quantity"] == 199  # 20% cap: 20000 / 100.2
    assert p["time_stop"] == "Square off by 15:05"


def test_extended_move_waits_for_vwap():
    f = {"price": 104.0, "vwap": 100.0, "hod": 104.2, "lod": 99.0, "adr_pct": 0.02, "bar_range": 0.2,
         "prev_high": 101, "prev_low": 97}
    p = it.plan(f, 1, "live", 0, 0.5, 20, None)
    assert p["extended_from_vwap"] and p["trigger"] < 101


def test_listing_filter_ranks_by_local_value_and_drops_lines():
    q = lambda s, name, vol, px=10.0, t="EQUITY": {"symbol": s, "longName": name, "averageDailyVolume3Month": vol,
                                                   "regularMarketPrice": px, "quoteType": t}
    quotes = [q("NVDC34.SA", "NVIDIA", 9e6), q("PETR4.SA", "Petrobras", 5e7), q("PETR3.SA", "Petrobras", 1e7),
              q("1NVDA.MI", "NVIDIA", 1e5), q("ENB-PY.TO", "Enbridge", 1e4), q("X.PA", "Bank 1.4% bond", 1e6),
              q("VALE3.SA", "Vale", 3e7), q("FUND.SA", "Fund", 1e8, t="ETF")]
    out = [x["symbol"] for x in it.filter_home_listings(quotes, 10)]
    assert out == ["PETR4.SA", "VALE3.SA"]


def test_universe_aliases():
    assert it.resolve_universe("Nifty 50").exchange_code == "NSE"
    assert it.resolve_universe("bank  nifty").sector == "Financial Services"
    assert it.resolve_universe("japan").exchange_code == "TSE"
    assert it.resolve_universe("mars") is None


def _session(prices):
    idx = pd.date_range(datetime(2026, 7, 1, 10, 0, tzinfo=TZ), periods=len(prices), freq="5min")
    p = np.array(prices, dtype=float)
    return pd.DataFrame({"Open": p, "High": p + 0.1, "Low": p - 0.1, "Close": p, "Volume": 1.0}, index=idx)


def test_intraday_scoring_target_stop_and_untriggered():
    e = {"symbol": "X", "direction": "LONG", "trigger": 100.0, "stop": 99.0, "targets": [101.0, 102.0], "p_follow": 0.6}
    win = journal.score_intraday(e, _session([99.5, 100.0, 100.5, 101.2]), complete=True)
    assert win["exit"] == "target 1" and win["r_multiple"] == 1.0 and win["hit"] is True
    loss = journal.score_intraday(e, _session([100.0, 99.5, 98.8]), complete=True)
    assert loss["exit"] == "stop" and loss["r_multiple"] == -1.0
    none = journal.score_intraday(e, _session([99.0, 98.5]), complete=True)
    assert none["triggered"] is False
    pending = journal.score_intraday(e, _session([99.0]), complete=False)
    assert pending["status"] == "open"


def test_intraday_journal_entry_validation(tmp_path, monkeypatch):
    monkeypatch.setenv("TRADEFLOOR_HOME", str(tmp_path))
    base = {"kind": "intraday", "symbol": "X", "exchange": "NSE", "direction": "LONG", "trigger": 1, "stop": 0.9, "targets": [1.1]}
    with pytest.raises(ValueError):
        journal.record({**base, "mode": "live"})  # no signal_time
    assert journal.record({**base, "mode": "live", "signal_time": "2026-07-01 10:30"})["id"]
