"""Technical indicators. Pure pandas, no look-ahead: every value at row t uses rows <= t.

The LLM never computes these. The paper's agents read raw indicator tables; here the
arithmetic is done once, in code, and the agents read the result.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def _wilder(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = _wilder(d.clip(lower=0), n)
    down = _wilder(-d.clip(upper=0), n)
    rs = up / down.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    # All gains and no losses: RSI is 100 by definition.
    return out.where(~((down == 0) & (up > 0)), 100.0)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    line = ema(close, fast) - ema(close, slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    mid = sma(close, n)
    sd = close.rolling(n, min_periods=n).std(ddof=0)
    upper, lower = mid + k * sd, mid - k * sd
    pct_b = (close - lower) / (upper - lower)
    return pd.DataFrame({"mid": mid, "upper": upper, "lower": lower, "pct_b": pct_b, "width": (upper - lower) / mid})


def true_range(df: pd.DataFrame) -> pd.Series:
    prev = df["Close"].shift(1)
    return pd.concat([df["High"] - df["Low"], (df["High"] - prev).abs(), (df["Low"] - prev).abs()], axis=1).max(axis=1)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return _wilder(true_range(df), n)


def adx(df: pd.DataFrame, n: int = 14) -> pd.DataFrame:
    up = df["High"].diff()
    down = -df["Low"].diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    tr = _wilder(true_range(df), n)
    plus_di = 100 * _wilder(plus_dm, n) / tr
    minus_di = 100 * _wilder(minus_dm, n) / tr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return pd.DataFrame({"adx": _wilder(dx, n), "plus_di": plus_di, "minus_di": minus_di})


def stochastic(df: pd.DataFrame, n: int = 14, d: int = 3) -> pd.DataFrame:
    lo = df["Low"].rolling(n, min_periods=n).min()
    hi = df["High"].rolling(n, min_periods=n).max()
    k = 100 * (df["Close"] - lo) / (hi - lo).replace(0, np.nan)
    return pd.DataFrame({"k": k, "d": k.rolling(d, min_periods=d).mean()})


def obv(df: pd.DataFrame) -> pd.Series:
    direction = np.sign(df["Close"].diff()).fillna(0)
    return (direction * df["Volume"].fillna(0)).cumsum()


def log_returns(close: pd.Series) -> pd.Series:
    return np.log(close).diff()


def realized_vol(close: pd.Series, n: int = 20, periods_per_year: int = 252) -> pd.Series:
    """Annualized close-to-close volatility."""
    return log_returns(close).rolling(n, min_periods=n).std() * np.sqrt(periods_per_year)


def ewma_vol_daily(close: pd.Series, lam: float = 0.94) -> pd.Series:
    """RiskMetrics EWMA daily volatility."""
    r2 = log_returns(close) ** 2
    return np.sqrt(r2.ewm(alpha=1 - lam, adjust=False, min_periods=20).mean())


def max_drawdown(close: pd.Series) -> float:
    peak = close.cummax()
    return float((close / peak - 1).min())


def swing_levels(df: pd.DataFrame, window: int = 5, lookback: int = 120, max_levels: int = 3) -> dict:
    """Nearest swing highs above and swing lows below the last close.

    A swing high at t is the max of [t-window, t+window]. Pivots need `window` bars on the
    right, so the last `window` bars never qualify: that is the no-look-ahead cost.
    """
    d = df.tail(lookback)
    hi, lo, close = d["High"], d["Low"], float(d["Close"].iloc[-1])
    span = 2 * window + 1
    piv_hi = hi[(hi == hi.rolling(span, center=True, min_periods=span).max())].dropna()
    piv_lo = lo[(lo == lo.rolling(span, center=True, min_periods=span).min())].dropna()
    res = sorted({round(float(x), 4) for x in piv_hi if x > close})[:max_levels]
    sup = sorted({round(float(x), 4) for x in piv_lo if x < close}, reverse=True)[:max_levels]
    return {"resistance": res, "support": sup}


def _r(x, nd: int = 2):
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    if np.isnan(f) or np.isinf(f):
        return None
    return round(f, nd)


def technical_summary(df: pd.DataFrame, bench: pd.DataFrame | None = None, periods_per_year: int = 252) -> dict:
    """Compact, rounded snapshot of the indicators the analysts need."""
    c = df["Close"]
    last = float(c.iloc[-1])
    s20, s50, s200 = sma(c, 20), sma(c, 50), sma(c, 200)
    m = macd(c)
    bb = bollinger(c)
    a = atr(df)
    dx = adx(df)
    st = stochastic(df)
    r = rsi(c)
    vol20 = realized_vol(c, 20, periods_per_year)
    vol_hist = vol20.dropna()
    vol_pct = float((vol_hist <= vol_hist.iloc[-1]).mean()) if len(vol_hist) > 60 else None

    def ret(n: int):
        return _r((last / float(c.iloc[-n - 1]) - 1) * 100) if len(c) > n else None

    s50_slope = _r((s50.iloc[-1] / s50.iloc[-21] - 1) * 100) if len(s50.dropna()) > 21 else None
    above_200 = None if np.isnan(s200.iloc[-1]) else bool(last > s200.iloc[-1])
    golden = None
    if not np.isnan(s200.iloc[-1]):
        golden = "50 above 200" if s50.iloc[-1] > s200.iloc[-1] else "50 below 200"

    adx_v = _r(dx["adx"].iloc[-1])
    if adx_v is None:
        trend_strength = None
    elif adx_v >= 25:
        trend_strength = "trending"
    elif adx_v >= 18:
        trend_strength = "weak trend"
    else:
        trend_strength = "range-bound"

    if above_200 is None:
        regime = "insufficient history for 200-day regime"
    elif above_200 and (s50_slope or 0) > 0:
        regime = "uptrend"
    elif not above_200 and (s50_slope or 0) < 0:
        regime = "downtrend"
    else:
        regime = "transition"

    vol_ma = df["Volume"].rolling(20, min_periods=20).mean().iloc[-1] if "Volume" in df else np.nan
    out = {
        "last_close": _r(last, 4),
        "last_date": str(df.index[-1].date()),
        "returns_pct": {"1w": ret(5), "1m": ret(21), "3m": ret(63), "6m": ret(126), "1y": ret(252)},
        "sma": {"20": _r(s20.iloc[-1]), "50": _r(s50.iloc[-1]), "200": _r(s200.iloc[-1]), "sma50_slope_1m_pct": s50_slope, "cross": golden},
        "regime": regime,
        "trend_strength": trend_strength,
        "adx": adx_v,
        "plus_di": _r(dx["plus_di"].iloc[-1]),
        "minus_di": _r(dx["minus_di"].iloc[-1]),
        "rsi14": _r(r.iloc[-1]),
        "macd": {"line": _r(m["macd"].iloc[-1], 4), "signal": _r(m["signal"].iloc[-1], 4), "hist": _r(m["hist"].iloc[-1], 4),
                 "hist_rising": bool(m["hist"].iloc[-1] > m["hist"].iloc[-2]) if len(m.dropna()) > 1 else None},
        "bollinger": {"upper": _r(bb["upper"].iloc[-1]), "lower": _r(bb["lower"].iloc[-1]), "pct_b": _r(bb["pct_b"].iloc[-1]), "width": _r(bb["width"].iloc[-1], 4)},
        "stochastic": {"k": _r(st["k"].iloc[-1]), "d": _r(st["d"].iloc[-1])},
        "atr14": _r(a.iloc[-1], 4),
        "atr_pct": _r(a.iloc[-1] / last * 100),
        "realized_vol_20d_ann_pct": _r(vol20.iloc[-1] * 100),
        "vol_percentile_vs_history": _r(vol_pct),
        "volume_vs_20d_avg": _r(df["Volume"].iloc[-1] / vol_ma) if vol_ma and not np.isnan(vol_ma) and vol_ma > 0 else None,
        "obv_trend_1m": ("rising" if obv(df).iloc[-1] > obv(df).iloc[-21] else "falling") if len(df) > 21 and df["Volume"].sum() > 0 else None,
        "range_52w": {"high": _r(c.tail(252).max()), "low": _r(c.tail(252).min()), "pct_from_high": _r((last / c.tail(252).max() - 1) * 100)},
        "max_drawdown_1y_pct": _r(max_drawdown(c.tail(252)) * 100),
        "levels": swing_levels(df),
    }
    lo52, hi52 = float(c.tail(252).min()), float(c.tail(252).max())
    if not out["levels"]["support"] and lo52 < last:
        out["levels"]["support"] = [_r(lo52, 4)]
        out["levels"]["note"] = "No swing low below price in 120 bars; support is the 52-week low."
    if not out["levels"]["resistance"] and hi52 > last:
        out["levels"]["resistance"] = [_r(hi52, 4)]
        out["levels"]["note"] = "No swing high above price in 120 bars; resistance is the 52-week high."
    if bench is not None and len(bench) > 63:
        b = bench["Close"].reindex(c.index).ffill()
        rel = c / b
        out["relative_strength_vs_benchmark_pct"] = {
            "1m": _r((rel.iloc[-1] / rel.iloc[-22] - 1) * 100) if len(rel.dropna()) > 22 else None,
            "3m": _r((rel.iloc[-1] / rel.iloc[-64] - 1) * 100) if len(rel.dropna()) > 64 else None,
        }
        lr, lb = log_returns(c).tail(252), log_returns(b).tail(252)
        both = pd.concat([lr, lb], axis=1).dropna()
        if len(both) > 60 and both.iloc[:, 1].var() > 0:
            out["beta_1y"] = _r(both.iloc[:, 0].cov(both.iloc[:, 1]) / both.iloc[:, 1].var())
            out["correlation_1y"] = _r(both.iloc[:, 0].corr(both.iloc[:, 1]))
    return out
