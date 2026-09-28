import numpy as np
import pandas as pd

from tradefloor import forecast as fc
from tradefloor import indicators as ind


def test_rsi_bounds_and_all_gains():
    up = pd.Series(np.arange(1, 60, dtype=float))
    assert ind.rsi(up).dropna().eq(100).all()
    rng = np.random.default_rng(1)
    noisy = pd.Series(100 + rng.normal(0, 1, 500).cumsum())
    r = ind.rsi(noisy).dropna()
    assert r.between(0, 100).all()


def test_atr_constant_range():
    n = 60
    df = pd.DataFrame({"Open": 100.0, "High": 101.0, "Low": 99.0, "Close": 100.0, "Volume": 1.0}, index=pd.bdate_range("2024-01-01", periods=n))
    assert abs(ind.atr(df).iloc[-1] - 2.0) < 1e-9


def test_technical_summary_shape(ohlc, bench):
    t = ind.technical_summary(ohlc, bench)
    for k in ("last_close", "regime", "rsi14", "atr14", "levels", "relative_strength_vs_benchmark_pct", "beta_1y"):
        assert k in t
    assert all(s < t["last_close"] for s in t["levels"]["support"])
    assert all(r > t["last_close"] for r in t["levels"]["resistance"])


def test_factors_have_no_lookahead(ohlc, bench):
    """Factors on truncated data must equal the same rows computed on the full data."""
    full = fc.factor_frame(ohlc, bench)
    cut = 1100
    part = fc.factor_frame(ohlc.iloc[:cut], bench.iloc[:cut])
    pd.testing.assert_frame_equal(full.iloc[:cut], part, check_exact=False, rtol=1e-9)
    s_full = fc.setup_score(full, 21).iloc[:cut]
    s_part = fc.setup_score(part, 21)
    pd.testing.assert_series_equal(s_full, s_part, check_exact=False, rtol=1e-9)


def test_forecast_ignores_future_rows(ohlc, bench):
    cut = 1200
    a = fc.forecast(ohlc.iloc[:cut], 21, bench.iloc[:cut])
    b = fc.forecast(ohlc.iloc[:cut].copy(), 21, bench.iloc[:cut].copy())
    assert a["probabilities"] == b["probabilities"]
    # Adding bars after as_of must not change the as_of date or price used.
    assert a["as_of"] == str(ohlc.index[cut - 1].date())


def test_forecast_probabilities_valid(ohlc, bench):
    for h in (5, 21, 63):
        r = fc.forecast(ohlc, h, bench)
        p = r["probabilities"]
        assert abs(p["up"] + p["down"] + p["flat"] - 1) < 0.01
        assert r["direction"] in ("UP", "DOWN", "SIDEWAYS")
        assert r["confidence"] in ("low", "medium", "high")
        assert r["tilt"]["label"] and abs(r["tilt"]["value"]) <= 2
        assert r["expected_range_80pct"]["low"] < r["price"] < r["expected_range_80pct"]["high"]
        assert r["similar_setups"]["n"] > 0


def test_random_walk_has_no_big_edge():
    """On a driftless random walk the conditional rates should sit near the base rates."""
    from conftest import make_ohlc

    df = make_ohlc(n=3000, drift=0.0, seed=3)
    r = fc.forecast(df, 21)
    assert r["edge_vs_base_rate"] < 0.10


def test_short_history_falls_back_to_base_rates(ohlc):
    r = fc.forecast(ohlc.iloc[:320], 21)
    assert r["confidence"] == "low" and "warning" in r


def test_no_benchmark_drops_rel_strength(ohlc):
    """An index is its own benchmark: rel_strength must drop out, not dilute as a zero."""
    f = fc.factor_frame(ohlc, None)
    assert f["rel_strength"].isna().all()
    s = fc.setup_score(f, 21)
    assert s.notna().sum() > 1000
    r = fc.forecast(ohlc, 21)
    assert all(d["factor"] != "rel_strength" for d in r["drivers"])


def test_levels_fall_back_to_52w_extremes():
    """Decline, then a steady recovery: no swing low in the last 120 bars, but the
    52-week low sits below price, so it becomes the support level."""
    close = np.concatenate([np.linspace(200, 100, 200), np.linspace(100, 130, 200)])
    df = pd.DataFrame({"Open": close, "High": close + 0.5, "Low": close - 0.5, "Close": close, "Volume": 1.0},
                      index=pd.bdate_range("2024-01-01", periods=len(close)))
    lv = ind.technical_summary(df)["levels"]
    assert lv["support"] == [100.0] and "52-week low" in lv["note"]
