"""Pre-market scouting: which stocks are likely to make a big move in the coming session.

Tested on 2026-09-27 over ~50 sessions of NIFTY 50, S&P 500 and DAX stocks: a stock that
was "in play" in the previous session (traded value and range well above its own normal)
was 2 to 3 times more likely to have a range-expansion day, while the direction of the
next day's move was close to a coin flip after strong days. So this ranks by the chance
of a big move and reports a direction lean only where the calibration shows one. The
plan is two-sided: the opening range decides the side.

Everything here uses only sessions that closed before the target session.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import intraday as it

LOOKBACK = 20
BIG_MOVE_X_ADR = 1.3  # a session whose high-low range is 1.3x the stock's average daily range
SHRINK_K = 30.0


def daily_table(sess: list[pd.DataFrame]) -> pd.DataFrame:
    """Per-session stats plus each session's opening-range size, computed once per stock."""
    d = it.daily_stats(sess)
    d["or_size"] = [float(x["High"].iloc[:it.ORB_BARS].max() - x["Low"].iloc[:it.ORB_BARS].min()) if len(x) >= it.ORB_BARS else np.nan for x in sess]
    return d


def features_at(d: pd.DataFrame, i: int) -> dict | None:
    """Features known before session i, from rows < i of a daily table."""
    if i < LOOKBACK + 1:
        return None
    last, base = d.iloc[i - 1], d.iloc[i - 1 - LOOKBACK:i - 1]
    adr = float(base["range_pct"].mean())
    avg_value = float(base["value"].mean())
    if adr <= 0 or avg_value <= 0 or last["close"] <= 0:
        return None
    rng = float(last["high"] - last["low"])
    ors = d["or_size"].iloc[max(0, i - 10):i].dropna()
    prev_ret = float(last["close"] / last["open"] - 1)
    return {
        "prev_close": float(last["close"]), "prev_high": float(last["high"]), "prev_low": float(last["low"]),
        "prev_ret": prev_ret, "prev_close_loc": (float(last["close"]) - float(last["low"])) / rng if rng > 0 else 0.5,
        "adr_pct": adr, "value_ratio": float(last["value"]) / avg_value, "range_ratio": float(last["range_pct"]) / adr,
        "strong_prev": abs(prev_ret) >= 0.5 * adr,
        "typical_or": float(ors.median()) if len(ors) else float("nan"),
        "session_date": last["date"],
    }


def features_before(prior: list[pd.DataFrame]) -> dict | None:
    """Everything knowable before the session that follows `prior`."""
    if len(prior) < LOOKBACK + 1:
        return None
    return features_at(daily_table(prior[-(LOOKBACK + 10):]), min(len(prior), LOOKBACK + 10))


def outcome(session: pd.DataFrame, adr_pct: float) -> dict:
    o, c = float(session["Open"].iloc[0]), float(session["Close"].iloc[-1])
    hi, lo = float(session["High"].max()), float(session["Low"].min())
    rng = (hi - lo) / c if c > 0 else 0.0
    return {"big_move": rng >= BIG_MOVE_X_ADR * adr_pct,
            "trend_day": abs(c / o - 1) >= 0.5 * adr_pct and abs(c - o) >= 0.6 * (hi - lo),
            "ret": c / o - 1}


def history(hist: dict[str, list[pd.DataFrame]]) -> pd.DataFrame:
    """One row per (stock, session): pre-session features and what the session did."""
    rows = []
    for sym, sess in hist.items():
        d = daily_table(sess)
        for i in range(LOOKBACK + 1, len(sess)):
            f = features_at(d, i)
            if f is None:
                continue
            row = d.iloc[i]
            rng = (row["high"] - row["low"]) / row["close"] if row["close"] > 0 else 0.0
            ret = row["close"] / row["open"] - 1
            big = rng >= BIG_MOVE_X_ADR * f["adr_pct"]
            trend = abs(ret) >= 0.5 * f["adr_pct"] and abs(row["close"] - row["open"]) >= 0.6 * (row["high"] - row["low"])
            same = None
            if f["strong_prev"] and ret != 0:
                same = (ret > 0) == (f["prev_ret"] > 0)
            rows.append({"symbol": sym, "date": row["date"], "value_ratio": f["value_ratio"], "range_ratio": f["range_ratio"],
                         "strong_prev": f["strong_prev"], "extreme_close": _extreme_close(f), "same_dir": same,
                         "big_move": bool(big), "trend_day": bool(trend)})
    return pd.DataFrame(rows)


def _extreme_close(f: dict) -> bool:
    """Closed in the top fifth of the range on an up day, or the bottom fifth on a down day."""
    return (f["prev_ret"] > 0 and f["prev_close_loc"] >= 0.8) or (f["prev_ret"] < 0 and f["prev_close_loc"] <= 0.2)


class InPlayScorer:
    """Score = mean percentile of log(value_ratio) and log(range_ratio) within the pool."""

    def __init__(self, pool: pd.DataFrame):
        lv = np.log(np.clip(pool["value_ratio"].to_numpy(dtype=float), 1e-6, None))
        lr = np.log(np.clip(pool["range_ratio"].to_numpy(dtype=float), 1e-6, None))
        self.v, self.r = np.sort(lv), np.sort(lr)
        n = max(1, len(lv))
        self.pool_scores = 0.5 * np.searchsorted(self.v, lv, side="right") / n + 0.5 * np.searchsorted(self.r, lr, side="right") / n

    @staticmethod
    def _pct(sorted_arr: np.ndarray, x: float) -> float:
        return float(np.searchsorted(sorted_arr, x, side="right")) / max(1, len(sorted_arr))

    def __call__(self, value_ratio: float, range_ratio: float) -> float:
        return 0.5 * self._pct(self.v, math.log(max(value_ratio, 1e-6))) + 0.5 * self._pct(self.r, math.log(max(range_ratio, 1e-6)))


def isotonic(rates: list[float], weights: list[float]) -> list[float]:
    """Pool-adjacent-violators: the closest non-decreasing sequence, so a more in-play
    bucket never gets a lower probability than a less in-play one because of noise."""
    blocks = [[r, w, 1] for r, w in zip(rates, weights)]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] > blocks[i + 1][0]:
            r1, w1, n1 = blocks[i]
            r2, w2, n2 = blocks.pop(i + 1)
            w = w1 + w2
            blocks[i] = [(r1 * w1 + r2 * w2) / w if w else (r1 + r2) / 2, w, n1 + n2]
            i = max(0, i - 1)
        else:
            i += 1
    out = []
    for r, _, n in blocks:
        out += [r] * n
    return out


def _shrunk(sub: pd.Series, base: float, n_days: int) -> tuple[float, float]:
    n_eff = min(float(len(sub)), 3.0 * n_days)
    w = n_eff / (n_eff + SHRINK_K)
    raw = float(sub.mean()) if len(sub) else base
    return w * raw + (1 - w) * base, n_eff


def probabilities(pool: pd.DataFrame, scorer: InPlayScorer, f: dict) -> dict:
    """Big-move and trend-day probabilities for f's in-play quintile, and a direction lean
    only when strong-day continuation in this pool departs from a coin flip."""
    if pool.empty or len(pool) < 100:
        return {"p_big_move": None, "note": "Too little history to calibrate."}
    scores = scorer.pool_scores
    s = scorer(f["value_ratio"], f["range_ratio"])
    buckets = 10 if len(pool) >= 1500 else 5
    edges = np.quantile(scores, np.linspace(0, 1, buckets + 1)[1:-1])
    q = int(np.searchsorted(edges, s, side="right"))
    labels = np.searchsorted(edges, scores, side="right")
    base_big, base_trend = float(pool["big_move"].mean()), float(pool["trend_day"].mean())
    smooth = {}
    for col, base in (("big_move", base_big), ("trend_day", base_trend)):
        rates, weights = [], []
        for b in range(buckets):
            part = pool[labels == b]
            rates.append(float(part[col].mean()) if len(part) else base)
            weights.append(float(len(part)))
        smooth[col] = isotonic(rates, weights)
    sub = pool[labels == q]
    n_days = sub["date"].nunique()
    p_big, n_eff = _shrunk(pd.Series([smooth["big_move"][q]] * len(sub)), base_big, n_days)
    p_trend, _ = _shrunk(pd.Series([smooth["trend_day"][q]] * len(sub)), base_trend, n_days)
    out = {"in_play_score": round(s, 3), "bucket": f"{q + 1} of {buckets}", "p_big_move": round(p_big, 3), "base_p_big_move": round(base_big, 3),
           "lift": round(p_big / base_big, 2) if base_big > 0 else None, "p_trend_day": round(p_trend, 3),
           "base_p_trend_day": round(base_trend, 3), "n": int(len(sub)), "n_effective": round(n_eff, 1)}
    out["direction"] = direction_lean(pool, f)
    return out


def direction_lean(pool: pd.DataFrame, f: dict) -> dict:
    if not f["strong_prev"]:
        return {"lean": None, "read": "No strong move yesterday: decide the side at the open."}
    strong = pool[pool["strong_prev"] & pool["same_dir"].notna() & (pool["extreme_close"] == _extreme_close(f))]
    if len(strong) < 50:
        return {"lean": None, "read": "Too little history for a direction lean: decide at the open."}
    p_cont, n_eff = _shrunk(strong["same_dir"].astype(float), 0.5, strong["date"].nunique())
    yesterday = "up" if f["prev_ret"] > 0 else "down"
    two_se = 2 * math.sqrt(0.25 / max(n_eff, 1.0))  # a lean must clear two standard errors from 50%
    if abs(p_cont - 0.5) < two_se:
        return {"lean": None, "p_continuation": round(p_cont, 3), "n_effective": round(n_eff, 1),
                "read": f"After strong {yesterday} days, the next day continued {p_cont:.0%} of the time here, within noise of a coin flip. Decide at the open."}
    if p_cont > 0.5:
        lean, side = "continuation", "LONG" if f["prev_ret"] > 0 else "SHORT"
    else:
        lean, side = "reversal", "SHORT" if f["prev_ret"] > 0 else "LONG"
    return {"lean": lean, "side": side, "p_continuation": round(p_cont, 3), "n_effective": round(n_eff, 1),
            "read": f"After strong {yesterday} days like this, the next day continued {p_cont:.0%} of the time here: a {lean} lean, so prefer the {side.lower()} break."}


def orb_plan(f: dict, lean_side: str | None, capital: float, risk_pct: float, max_position_pct: float, square_off: str | None) -> dict:
    """Two-sided opening-range plan. Levels are set by the first 15 minutes, so this gives
    rules plus sizing from the stock's typical opening range."""
    price = f["prev_close"]
    adr_abs = f["adr_pct"] * price
    risk = f["typical_or"] if math.isfinite(f["typical_or"]) and f["typical_or"] > 0 else 0.25 * adr_abs
    out = {
        "rule": ("Wait for the first 15 minutes. Long on a break above the opening-range high, stop at the opening-range low; "
                 "short on a break below the low, stop at the high. Targets: 1x and 2x the opening range from the trigger."),
        "prefer": lean_side or "either: the first clean break with volume decides",
        "skip_if": f"the opening range is wider than {0.5 * adr_abs:.4g} (half the average daily range), or the stock gaps beyond yesterday's high {f['prev_high']:.4g} / low {f['prev_low']:.4g} and reverses into the range",
        "reference_levels": {"prev_high": round(f["prev_high"], 4), "prev_low": round(f["prev_low"], 4), "prev_close": round(price, 4)},
        "typical_opening_range": round(risk, 4),
        "typical_opening_range_pct": round(risk / price * 100, 2),
        "time_stop": f"Square off by {square_off}" if square_off else "Square off before the close",
    }
    if capital and capital > 0 and risk > 0:
        qty = math.floor(capital * risk_pct / 100 / risk)
        cap = math.floor(capital * max_position_pct / 100 / price)
        out["size_estimate"] = {"quantity": max(0, min(qty, cap)), "risk_pct": risk_pct, "capped": qty > cap,
                                "note": "Estimated from the typical opening range; recompute once the actual range is set."}
    return out


def simulate_orb(session: pd.DataFrame, adr_abs: float, side: str | None = None) -> dict:
    """Two-sided opening-range trade on one session's 5-minute bars.

    The range is the first 15 minutes. The first later bar to trade through its high (long)
    or low (short) triggers; the stop is the other side of the range, the target twice the
    range from the trigger. A bar touching both stop and target counts as the stop. Otherwise
    the trade exits at the close. Skipped when the range is wider than half the ADR.
    `side` restricts to LONG or SHORT breaks when a lean was given."""
    if len(session) <= it.ORB_BARS:
        return {"status": "no data"}
    opening = session.iloc[:it.ORB_BARS]
    orh, orl = float(opening["High"].max()), float(opening["Low"].min())
    size = orh - orl
    if size <= 0:
        return {"status": "no range"}
    if adr_abs and size > 0.5 * adr_abs:
        return {"status": "skipped", "reason": "opening range wider than half the ADR", "or_size": round(size, 4)}
    rest = session.iloc[it.ORB_BARS:]
    for ts, bar in rest.iterrows():
        up = bar["High"] > orh and side in (None, "LONG")
        down = bar["Low"] < orl and side in (None, "SHORT")
        if not (up or down):
            continue
        if up and down:
            return {"status": "scored", "triggered": True, "side": "BOTH", "r_multiple": -1.0, "exit": "stop (range broken both ways in one bar)"}
        d, trig, stop = (1, orh, orl) if up else (-1, orl, orh)
        target = trig + d * 2 * size
        after = rest.loc[ts:]
        stop_hit = after["Low"] <= stop if d > 0 else after["High"] >= stop
        tgt_hit = after["High"] >= target if d > 0 else after["Low"] <= target
        fs = stop_hit.idxmax() if stop_hit.any() else None
        ft = tgt_hit.idxmax() if tgt_hit.any() else None
        if fs is not None and (ft is None or fs <= ft):
            r, how = -1.0, "stop"
        elif ft is not None:
            r, how = 2.0, "target"
        else:
            r, how = d * (float(after["Close"].iloc[-1]) - trig) / size, "close"
        return {"status": "scored", "triggered": True, "side": "LONG" if d > 0 else "SHORT", "r_multiple": round(r, 2), "exit": how}
    return {"status": "scored", "triggered": False, "r_multiple": 0.0}
