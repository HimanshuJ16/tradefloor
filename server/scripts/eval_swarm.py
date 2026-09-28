"""Is the swarm's baseline honest about uncertainty? For each stock and each past date, the
baseline simulation (no news reactions) gives an 80% range for the next month; a calibrated
simulator should contain about 80% of the real outcomes. The quant model's 80% range is
scored on the same dates for comparison.

    uv run python scripts/eval_swarm.py "nifty 50" --json ../benchmarks/results/<date>-swarm-calibration.json
"""

import json
import sys
from datetime import datetime

import numpy as np
import pandas as pd

from tradefloor import data, forecast, markets, scout, swarm

H, N_STOCKS, N_DATES, STEP = 21, 15, 12, 21


def evaluate(market: str) -> dict:
    uni = scout.build_universe(market, None)
    code = uni["exchange"]
    rows = []
    for sym in uni["symbols"][:N_STOCKS]:
        full = data.history(sym, None, 12)
        if len(full) < 800:
            continue
        ends = [len(full) - 1 - H - i * STEP for i in range(N_DATES)]
        for end in ends:
            df = full.iloc[: end + 1]
            realized = float(full["Close"].iloc[end + H] / full["Close"].iloc[end] - 1) * 100
            sim = swarm.run(df, code, H, runs=400, agents=1000, seed=end)
            b = sim["baseline"]["return_pct"]
            fc = forecast.forecast(df, H)
            lo = (fc["expected_range_80pct"]["low"] / fc["price"] - 1) * 100
            hi = (fc["expected_range_80pct"]["high"] / fc["price"] - 1) * 100
            rows.append({"symbol": sym, "as_of": str(df.index[-1].date()), "realized": realized,
                         "swarm_in": b["p10"] <= realized <= b["p90"], "swarm_below": realized < b["p10"],
                         "quant_in": lo <= realized <= hi, "swarm_width": b["p90"] - b["p10"], "quant_width": hi - lo})
    D = pd.DataFrame(rows)
    return {"market": market, "stocks": int(D["symbol"].nunique()), "cases": len(D),
            "first_as_of": min(D["as_of"]), "last_as_of": max(D["as_of"]),
            "swarm_coverage_80": round(float(D["swarm_in"].mean()), 3),
            "swarm_below_p10": round(float(D["swarm_below"].mean()), 3),
            "quant_coverage_80": round(float(D["quant_in"].mean()), 3),
            "swarm_avg_width_pct": round(float(D["swarm_width"].mean()), 2), "quant_avg_width_pct": round(float(D["quant_width"].mean()), 2)}


if __name__ == "__main__":
    args, out = sys.argv[1:], None
    if "--json" in args:
        i = args.index("--json"); out = args[i + 1]; args = args[:i] + args[i + 2:]
    res = [evaluate(m) for m in (args or ["nifty 50"])]
    for r in res:
        print(f"== {r['market']}: {r['cases']} cases ({r['stocks']} stocks, as_of {r['first_as_of']} to {r['last_as_of']}), horizon {H} trading days")
        print(f"   80% range contains the outcome: swarm baseline {r['swarm_coverage_80']:.0%} (avg width {r['swarm_avg_width_pct']}%), quant model {r['quant_coverage_80']:.0%} (avg width {r['quant_avg_width_pct']}%)")
        print(f"   below the swarm's 10th percentile: {r['swarm_below_p10']:.0%} (calibrated: 10%)")
    if out:
        json.dump({"ran_at": datetime.now().astimezone().isoformat(timespec="seconds"), "horizon_days": H, "markets": res}, open(out, "w", encoding="utf-8"), indent=2)
        print("wrote", out)
