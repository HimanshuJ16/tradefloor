import numpy as np
import pytest

from tradefloor import swarm
from conftest import make_ohlc


@pytest.fixture(scope="module")
def df():
    return make_ohlc(n=1200, drift=0.0003, vol=0.012, seed=5)


def test_rosters_normalise_and_accept_overrides():
    for code in ("NSE", "US", "XETRA"):
        g = swarm.roster(code)
        assert abs(sum(x.weight for x in g) - 1) < 1e-9 and len(g) == 6
    g = swarm.roster("NSE", {"retail": 3.0})
    assert max(g, key=lambda x: x.weight).id == "retail"


def test_reaction_parsing_clips_values():
    r = swarm.Reaction.parse({"group": "fii", "sentiment": 4, "conviction": -1, "persistence_days": 500, "fair_value_shift_pct": None})
    assert (r.sentiment, r.conviction, r.persistence_days, r.fair_value_shift_pct) == (1.0, 0.0, 60.0, 0.0)


def test_baseline_matches_the_stock_horizon_spread(df):
    prof = swarm.stock_profile(df, 21)
    groups = swarm.roster("NSE")
    noise = swarm.calibrate_noise(prof, groups, 21, 800, seed=3)
    sim = swarm._simulate(prof, groups, {}, 21, 600, 800, noise, seed=4)
    assert sim["final"].std() == pytest.approx(prof["sigma_d"] * np.sqrt(21), rel=0.15)


def test_same_seed_same_answer(df):
    a = swarm.run(df, "NSE", 10, runs=200, agents=400, seed=9)
    b = swarm.run(df, "NSE", 10, runs=200, agents=400, seed=9)
    assert a["baseline"] == b["baseline"]


def test_bullish_reactions_shift_odds_up_and_are_attributed(df):
    bull = [{"group": g, "sentiment": 0.9, "conviction": 0.9, "persistence_days": 10} for g in ("fii", "dii", "retail")]
    out = swarm.run(df, "NSE", 21, bull, runs=400, agents=800, seed=2)
    assert out["shift"]["p_up"] > 0.05 and out["shift"]["median_return_pct"] > 0
    movers = {m["group"]: m["moved_price_pct"] for m in out["who_moved_the_price"]}
    assert movers["retail"] > 0 and movers["fii"] > 0
    bear = [{**r, "sentiment": -0.9} for r in bull]
    out2 = swarm.run(df, "NSE", 21, bear, runs=400, agents=800, seed=2)
    assert out2["shift"]["p_down"] > 0.05


def test_probabilities_sum_to_one_and_unknown_groups_warn(df):
    out = swarm.run(df, "US", 5, [{"group": "martians", "sentiment": 1}], runs=200, agents=400, seed=1)
    b = out["baseline"]
    assert abs(b["p_up"] + b["p_down"] + b["p_flat"] - 1) < 0.01
    assert "martians" in out["warning"]
