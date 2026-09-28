"""Direction forecast: a transparent factor score, calibrated on the symbol's own history.

How it works, in order:
1. A setup score in [-1, 1] is computed for every past day from trend, momentum, MACD,
   short-horizon mean reversion and relative strength. Weights depend on the horizon.
   The weights are hand-set priors from the momentum and reversal literature, not fitted.
2. Every past day whose forward window closes on or before `as_of` is labelled with its
   forward return over the horizon: up, down, or flat (inside a volatility-scaled band).
3. Today's score is placed in a quintile of the historical score distribution. The
   up/down/flat frequencies inside that quintile are the conditional base rates.
4. Those rates are shrunk toward the unconditional base rates in proportion to the
   effective sample size. Forward windows overlap, so n_eff is roughly n / horizon.

The score only defines what "a similar setup" means. The probabilities come from what
actually happened after similar setups on this instrument. If the score has no edge on
this symbol, the conditional rates collapse to the base rates and the output says so.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ind

FLAT_BAND_SIGMA = 0.25  # |forward return| below 0.25 sigma of the horizon counts as flat
SHRINK_K = 20.0  # pseudo-observations pulling conditional rates to the base rate
DIRECTION_MARGIN = 0.08  # p_up must beat p_down by this much to call a direction
TILT_MARGIN = 0.06  # net (up - down) must differ from the base net by this much
MIN_ROWS = 300


def _weights(h: int) -> dict[str, float]:
    if h <= 10:
        return {"trend": 0.20, "mom_3m": 0.15, "mom_12_1": 0.05, "macd": 0.20, "reversion": 0.25, "rel_strength": 0.15}
    if h <= 63:
        return {"trend": 0.30, "mom_3m": 0.25, "mom_12_1": 0.20, "macd": 0.10, "reversion": 0.0, "rel_strength": 0.15}
    return {"trend": 0.30, "mom_3m": 0.15, "mom_12_1": 0.40, "macd": 0.0, "reversion": 0.0, "rel_strength": 0.15}


def _squash(x: pd.Series) -> pd.Series:
    """Scale-free squash: divide by the expanding std known at t, then tanh."""
    sd = x.expanding(min_periods=60).std()
    return np.tanh(x / sd.replace(0, np.nan))


def factor_frame(df: pd.DataFrame, bench: pd.DataFrame | None = None) -> pd.DataFrame:
    c = df["Close"]
    s50, s200 = ind.sma(c, 50), ind.sma(c, 200)
    a = ind.atr(df)
    f = pd.DataFrame(index=df.index)
    # Distance from the 200-day plus the sign of the 50-day slope.
    f["trend"] = _squash(c / s200 - 1) * 0.7 + np.sign(s50.diff(20)) * 0.3
    f["mom_3m"] = _squash(c / c.shift(63) - 1)
    f["mom_12_1"] = _squash(c.shift(21) / c.shift(252) - 1)
    f["macd"] = _squash(ind.macd(c)["hist"] / a)
    # Short-horizon reversal: oversold is bullish, overbought is bearish.
    f["reversion"] = ((50 - ind.rsi(c)) / 50).clip(-1, 1)
    if bench is not None and len(bench) > 100:
        b = bench["Close"].reindex(c.index).ffill()
        f["rel_strength"] = _squash((c / b) / (c / b).shift(63) - 1)
    else:
        # No benchmark (the instrument is its own benchmark): the factor drops out and the
        # remaining weights are renormalized, rather than a constant zero diluting them.
        f["rel_strength"] = np.nan
    return f


def setup_score(f: pd.DataFrame, h: int) -> pd.Series:
    w = _weights(h)
    cols = [k for k, v in w.items() if v > 0 and f[k].notna().any()]
    sub = f[cols]
    total = sum(w[k] for k in cols)
    return (sum(sub[k] * w[k] for k in cols) / total).where(sub.notna().all(axis=1))


def _label(fwd: pd.Series, band: pd.Series) -> pd.Series:
    lab = pd.Series(np.where(fwd > band, 1, np.where(fwd < -band, -1, 0)), index=fwd.index)
    return lab.where(fwd.notna() & band.notna())


def _rates(lab: pd.Series) -> dict[str, float]:
    n = len(lab)
    if n == 0:
        return {"up": np.nan, "down": np.nan, "flat": np.nan}
    return {"up": float((lab == 1).mean()), "down": float((lab == -1).mean()), "flat": float((lab == 0).mean())}


def forecast(df: pd.DataFrame, horizon_days: int, bench: pd.DataFrame | None = None) -> dict:
    """df must already be truncated at as_of. Nothing after the last row is read."""
    h = int(horizon_days)
    c = df["Close"].astype(float)
    price = float(c.iloc[-1])
    logc = np.log(c)
    daily_sd = ind.log_returns(c).rolling(63, min_periods=40).std()
    fwd = logc.shift(-h) - logc  # NaN for the last h rows: their future is unknown at as_of
    band = FLAT_BAND_SIGMA * daily_sd * np.sqrt(h)

    f = factor_frame(df, bench)
    score = setup_score(f, h)
    cur_score = score.iloc[-1]
    cur_factors = {k: (None if pd.isna(v) else round(float(v), 3)) for k, v in f.iloc[-1].items()}
    w = _weights(h)

    # Volatility floor: the current EWMA estimate, but never below the past year's realised
    # volatility. EWMA alone gave 80% ranges that held 69-73% of one-month outcomes.
    lr_1y = ind.log_returns(c).tail(252)
    sigma_d = max(float(ind.ewma_vol_daily(c).iloc[-1]), float(lr_1y.std()) if len(lr_1y) > 60 else 0.0)
    sigma_h = sigma_d * np.sqrt(h)

    lab = _label(fwd, band)
    hist = pd.DataFrame({"score": score, "lab": lab, "fwd": fwd}).dropna()
    base = _rates(hist["lab"])

    result: dict = {
        "horizon_trading_days": h,
        "price": round(price, 4),
        "as_of": str(df.index[-1].date()),
        "setup_score": None if pd.isna(cur_score) else round(float(cur_score), 3),
        "factors": {k: {"value": cur_factors.get(k), "weight": w[k]} for k in w},
        "volatility": {"daily_ewma_pct": round(sigma_d * 100, 3), "horizon_1sigma_pct": round(sigma_h * 100, 2)},
        "base_rates": {k: round(v, 3) for k, v in base.items()},
        "history_rows": int(len(hist)),
    }

    enough = len(hist) >= MIN_ROWS and not pd.isna(cur_score)
    if enough:
        edges = np.quantile(hist["score"], [0.2, 0.4, 0.6, 0.8])
        bucket = int(np.searchsorted(edges, cur_score, side="right"))
        hb = np.searchsorted(edges, hist["score"].to_numpy(), side="right")
        sub = hist[hb == bucket]
        cond = _rates(sub["lab"])
        n = len(sub)
        n_eff = n / max(1.0, float(h))
        wt = n_eff / (n_eff + SHRINK_K)
        p = {k: wt * cond[k] + (1 - wt) * base[k] for k in base}
        drift = float(sub["fwd"].median()) * wt
        q10, q90 = (float(x) for x in np.quantile(sub["fwd"], [0.1, 0.9]))
        result["similar_setups"] = {
            "quintile": bucket + 1,
            "n": n,
            "n_effective": round(n_eff, 1),
            "raw_rates": {k: round(v, 3) for k, v in cond.items()},
            "median_fwd_return_pct": round(float(np.expm1(sub["fwd"].median())) * 100, 2),
            "p10_fwd_return_pct": round(float(np.expm1(q10)) * 100, 2),
            "p90_fwd_return_pct": round(float(np.expm1(q90)) * 100, 2),
        }
    else:
        p = dict(base) if not any(np.isnan(v) for v in base.values()) else {"up": 1 / 3, "down": 1 / 3, "flat": 1 / 3}
        drift = 0.0
        result["similar_setups"] = None
        result["warning"] = f"Fewer than {MIN_ROWS} labelled rows or no score today; probabilities are unconditional base rates."

    z = 1.2816  # 80% two-sided under a normal approximation
    result["probabilities"] = {k: round(v, 3) for k, v in p.items()}
    result["expected_range_80pct"] = {
        "low": round(price * float(np.exp(drift - z * sigma_h)), 4),
        "high": round(price * float(np.exp(drift + z * sigma_h)), 4),
        "method": "max(EWMA, 1-year) volatility x sqrt(horizon), centred on the shrunk median drift of similar setups",
    }

    diff = p["up"] - p["down"]
    if diff >= DIRECTION_MARGIN:
        direction = "UP"
    elif -diff >= DIRECTION_MARGIN:
        direction = "DOWN"
    else:
        direction = "SIDEWAYS"
    edge = max(abs(p["up"] - base["up"]), abs(p["down"] - base["down"])) if enough else 0.0
    n_eff = result["similar_setups"]["n_effective"] if enough else 0
    if not enough or n_eff < 30 or edge < 0.04:
        confidence = "low"
    elif edge < 0.08:
        confidence = "medium"
    else:
        confidence = "high"
    # Most equities drift up, so "UP" alone often just restates the base rate. The tilt
    # says whether today's setup is more or less bullish than this symbol's normal.
    tilt = (p["up"] - p["down"]) - (base["up"] - base["down"]) if enough else 0.0
    if tilt >= TILT_MARGIN:
        tilt_label = "bullish tilt vs base rate"
    elif tilt <= -TILT_MARGIN:
        tilt_label = "bearish tilt vs base rate"
    else:
        tilt_label = "no tilt: in line with this symbol's base rate"
    result["direction"] = direction
    result["confidence"] = confidence
    result["tilt"] = {"value": round(tilt, 3), "label": tilt_label}
    result["edge_vs_base_rate"] = round(edge, 3)
    # The score describes the setup; the tilt says how such setups resolved. When they
    # point opposite ways the symbol has tended to mean-revert from this kind of setup.
    if enough and abs(tilt) >= TILT_MARGIN and cur_score * tilt < 0 and abs(cur_score) >= 0.15:
        setup = "bearish" if cur_score < 0 else "bullish"
        after = "gains" if tilt > 0 else "losses"
        result["setup_vs_outcome"] = (
            f"The setup reads {setup} (score {cur_score:+.2f}), but on this symbol similar setups were "
            f"followed by {after} more often than usual: historically it has mean-reverted from here."
        )
    result["drivers"] = _drivers(cur_factors, w)
    result["caveats"] = [
        "Probabilities are historical frequencies on this symbol after similar setups, not a guarantee.",
        "Factor weights are fixed priors, not fitted; the calibration comes from the symbol's own history.",
        "Price-only model: it does not see earnings dates, news, or macro events. The analysts add that.",
    ]
    return result


def _drivers(factors: dict, w: dict) -> list[dict]:
    rows = []
    for k, wt in w.items():
        v = factors.get(k)
        if wt == 0 or v is None:
            continue
        rows.append({"factor": k, "contribution": round(v * wt, 3), "reading": "bullish" if v > 0.15 else "bearish" if v < -0.15 else "neutral"})
    return sorted(rows, key=lambda r: -abs(r["contribution"]))
