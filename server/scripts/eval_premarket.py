"""Walk-forward check of the pre-market model on real data.

For each of the last N sessions, the model sees only earlier sessions, picks the top K
in-play stocks, and is graded on what that session did: big-move rate and a two-sided
opening-range trade, against every other stock in the universe the same day.

    uv run python scripts/eval_premarket.py "nifty 50" "s&p 500" dax
"""

import sys
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from tradefloor import data, intraday as it, markets, premarket as pm, scout

N_DAYS, TOP_K = 15, 5


def evaluate(market: str) -> dict:
    uni = scout.build_universe(market, None)
    ex = markets.EXCHANGES[uni["exchange"]]
    bars = data.intraday_bars(uni["symbols"], tz=ex.tz)
    hist = {s: it.sessions(df) for s, df in bars.items()}
    hist = {s: v for s, v in hist.items() if len(v) >= pm.LOOKBACK + 10}
    dates = sorted({x.index[0].date() for v in hist.values() for x in v})
    picks_rows, all_rows = [], []
    for target in dates[-N_DAYS:]:
        prior = {s: [x for x in v if x.index[0].date() < target] for s, v in hist.items()}
        prior = {s: v for s, v in prior.items() if len(v) >= pm.LOOKBACK + 2}
        pool = pm.history(prior)
        if len(pool) < 100:
            continue
        scorer = pm.InPlayScorer(pool)
        values = {s: float(np.median(it.daily_stats(v[-20:])["value"])) for s, v in prior.items()}
        floor = float(np.quantile(list(values.values()), 0.3))
        day = []
        for s, v in prior.items():
            today = [x for x in hist[s] if x.index[0].date() == target]
            f = pm.features_before(v)
            if not today or f is None or values[s] < floor or f["adr_pct"] < 0.008:
                continue
            sess = today[0]
            o = pm.outcome(sess, f["adr_pct"])
            orb = pm.simulate_orb(sess, f["adr_pct"] * f["prev_close"])
            day.append({"symbol": s, "date": target, "score": scorer(f["value_ratio"], f["range_ratio"]),
                        "big_move": o["big_move"], "trend_day": o["trend_day"],
                        "orb_r": orb.get("r_multiple") if orb.get("status") == "scored" else np.nan,
                        "orb_triggered": orb.get("triggered", False)})
        if not day:
            continue
        day = sorted(day, key=lambda r: -r["score"])
        for i, r in enumerate(day):
            (picks_rows if i < TOP_K else all_rows).append(r)
    P, R = pd.DataFrame(picks_rows), pd.DataFrame(all_rows)
    return {
        "market": market, "sessions": int(P["date"].nunique()), "picks": len(P), "others": len(R),
        "big_move_picks": P["big_move"].mean(), "big_move_others": R["big_move"].mean(),
        "trend_day_picks": P["trend_day"].mean(), "trend_day_others": R["trend_day"].mean(),
        "orb_avg_r_picks": P["orb_r"].mean(), "orb_avg_r_others": R["orb_r"].mean(),
        "orb_trades_picks": int(P["orb_triggered"].sum()), "orb_trades_others": int(R["orb_triggered"].sum()),
    }


if __name__ == "__main__":
    for m in sys.argv[1:] or ["nifty 50"]:
        r = evaluate(m)
        print(f"== {r['market']}: {r['sessions']} sessions walk-forward, top {TOP_K} picks/day ({r['picks']}) vs the rest ({r['others']} stock-days)")
        print(f"   big move (range >= {pm.BIG_MOVE_X_ADR}x ADR): picks {r['big_move_picks']:.0%}  vs rest {r['big_move_others']:.0%}")
        print(f"   trend day:                     picks {r['trend_day_picks']:.0%}  vs rest {r['trend_day_others']:.0%}")
        print(f"   two-sided ORB, avg R per stock: picks {r['orb_avg_r_picks']:+.2f} ({r['orb_trades_picks']} trades)  vs rest {r['orb_avg_r_others']:+.2f} ({r['orb_trades_others']} trades)")
