"""Intraday momentum scanner: which liquid stocks in a market are moving with strong,
clean, volume-backed direction right now, and how often has that followed through.

Method, per stock, at the same number of 5-minute bars into the session as "now":
  direction  the side of VWAP the price is on, if it agrees with the move since the open
  strength   relative volume at this time of day, efficiency of the move (net move over
             path length), size of the move against the stock's average daily range,
             opening-range break in the direction, and strength against the index
  score      direction x weighted strength, in [-1, 1]

Calibration: the same score is computed for every stock in the universe on each of the
previous sessions (up to ~60 days of 5-minute history), at the same bar count. Its outcome
is the rest-of-session move: follow-through, fade, or flat (inside 0.1 x ADR). Today's
candidates get the follow-through rate of past setups in the same score quintile, shrunk
toward the pooled base rate. Before the open the scan is premarket.py's instead: stocks
likely to make a big move, not a live momentum signal.

All arithmetic is here, in code. Agents interpret it.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

BAR_MINUTES = 5
ORB_BARS = 3  # 15-minute opening range
MIN_BARS_LIVE = 3
WEIGHTS = {"rvol": 0.30, "efficiency": 0.25, "move": 0.15, "orb": 0.15, "rel_strength": 0.15}
SHRINK_K = 30.0


# ------------------------------------------------------------------ universes

@dataclass(frozen=True)
class UniverseSpec:
    region: str
    exchanges: tuple[str, ...]
    exchange_code: str  # key into markets.EXCHANGES, for benchmark and timezone
    size: int
    label: str
    sector: str | None = None


def _u(region, exchanges, code, size, label, sector=None):
    return UniverseSpec(region, tuple(exchanges), code, size, label, sector)


_IN = ("in", ["NSI"], "NSE")
UNIVERSES: dict[str, UniverseSpec] = {}
for names, spec in [
    (["nifty 50", "nifty", "india", "nse", "sensex", "indian stocks"], _u(*_IN, 60, "60 most-traded NSE stocks (approximates the NIFTY 50)")),
    (["bank nifty", "nifty bank", "india banks", "indian banks"], _u(*_IN, 25, "25 most-traded NSE financial-services stocks (approximates NIFTY Bank)", "Financial Services")),
    (["nifty 500", "india broad", "nse 150"], _u(*_IN, 150, "150 most-traded NSE stocks")),
    (["s&p 500", "sp500", "spx", "us", "usa", "america", "us stocks", "dow"], _u("us", ["NMS", "NYQ"], "US", 100, "100 most-traded stocks on NYSE and Nasdaq")),
    (["nasdaq 100", "nasdaq", "ndx"], _u("us", ["NMS"], "US", 100, "100 most-traded Nasdaq stocks (approximates the Nasdaq 100)")),
    (["dax", "germany", "xetra", "german stocks"], _u("de", ["GER"], "XETRA", 60, "60 most-traded German companies on Xetra")),
    (["ftse 100", "ftse", "uk", "london", "british stocks"], _u("gb", ["LSE"], "LSE", 100, "100 most-traded UK companies on the LSE")),
    (["nikkei", "nikkei 225", "japan", "topix", "japanese stocks"], _u("jp", ["JPX"], "TSE", 100, "100 most-traded Japanese companies on the TSE")),
    (["hang seng", "hong kong", "hsi"], _u("hk", ["HKG"], "HKEX", 80, "80 most-traded Hong Kong companies on HKEX")),
    (["cac 40", "cac", "france", "paris"], _u("fr", ["PAR"], "EPA", 60, "60 most-traded French companies on Euronext Paris")),
    (["asx 200", "asx", "australia"], _u("au", ["ASX"], "ASX", 80, "80 most-traded Australian companies on the ASX")),
    (["tsx", "canada", "toronto"], _u("ca", ["TOR"], "TSX", 80, "80 most-traded Canadian companies on the TSX")),
    (["kospi", "korea", "south korea"], _u("kr", ["KSC"], "KRX", 80, "80 most-traded Korean companies on KOSPI")),
    (["taiex", "taiwan"], _u("tw", ["TAI"], "TWSE", 80, "80 most-traded Taiwanese companies on TWSE")),
    (["ibovespa", "brazil", "b3"], _u("br", ["SAO"], "B3", 80, "80 most-traded Brazilian companies on B3")),
    (["sti", "singapore"], _u("sg", ["SES"], "SGX", 50, "50 most-traded Singapore companies on SGX")),
    (["jse", "south africa"], _u("za", ["JNB"], "JSE", 60, "60 most-traded South African companies on the JSE")),
    (["tadawul", "saudi", "saudi arabia"], _u("sa", ["SAU"], "TADAWUL", 60, "60 most-traded Saudi companies on Tadawul")),
    (["smi", "switzerland", "swiss"], _u("ch", ["EBS"], "SIX", 40, "40 most-traded Swiss companies on SIX")),
    (["aex", "netherlands", "amsterdam"], _u("nl", ["AMS"], "AMS", 40, "40 most-traded Dutch companies on Euronext Amsterdam")),
    (["ibex", "ibex 35", "spain"], _u("es", ["MCE"], "BME", 40, "40 most-traded Spanish companies on BME")),
    (["ftse mib", "italy", "milan"], _u("it", ["MIL"], "BIT", 50, "50 most-traded Italian companies on Borsa Italiana")),
    (["china", "shanghai", "shenzhen", "a shares", "csi 300"], _u("cn", ["SHH", "SHZ"], "SSE", 100, "100 most-traded China A-share companies (Shanghai and Shenzhen)")),
]:
    for n in names:
        UNIVERSES[n] = spec

# Rules that decide whether "intraday" is even possible, by region.
MARKET_NOTES = {
    "cn": "China A-shares settle T+1: shares bought today cannot be sold today. Intraday here only means trading around existing holdings.",
    "us": "US pattern-day-trader rule: margin accounts under USD 25,000 are limited to 3 day trades in 5 business days.",
    "in": "India: intraday (MIS) positions are squared off by the broker before the close, typically 15:15 to 15:20 IST.",
    "kr": "Korea: short selling rules have changed repeatedly; check current KRX rules before shorting.",
}


def normalize(market: str) -> str:
    return " ".join(market.lower().replace("_", " ").split())


def resolve_universe(market: str) -> UniverseSpec | None:
    return UNIVERSES.get(normalize(market))


_NOT_ORDINARY = [
    re.compile(r"\d{2}\.SA$"),  # Brazilian BDRs: NVDC34.SA (home shares end 3, 4, 5, 6 or 11)
    re.compile(r"^1[A-Z].*\.MI$"),  # Borsa Italiana's foreign segment: 1NVDA.MI
    re.compile(r"-P[A-Z0-9]*\."),  # preferred lines: ENB-PY.TO
]


def _name(q: dict) -> str:
    return " ".join(str(q.get("longName") or q.get("shortName") or q["symbol"]).lower().split())


def local_value(q: dict) -> float:
    """Average daily traded value on this venue: what an intraday trader actually needs."""
    return float(q.get("averageDailyVolume3Month") or 0) * float(q.get("regularMarketPrice") or 0)


def filter_home_listings(quotes: list[dict], size: int) -> list[dict]:
    """The `size` most-traded ordinary shares on the venue.

    Yahoo's quote fields carry no reliable home-country flag (`region` reads US for NSE
    stocks, and euro-zone companies cross-list on each other's exchanges in the same
    currency), so the universe is ranked by local traded value instead of market cap.
    Cross-listings trade thinly away from home and fall out; known non-ordinary lines
    (Brazilian BDRs, Milan's foreign segment, preferreds, bond-like lines) are dropped first.
    Duplicate share lines of one company keep the most traded."""
    best: dict[str, dict] = {}
    for q in quotes:
        if q.get("quoteType") != "EQUITY" or local_value(q) <= 0 or "%" in _name(q):
            continue
        if any(p.search(q["symbol"]) for p in _NOT_ORDINARY):
            continue
        n = _name(q)
        if n not in best or local_value(q) > local_value(best[n]):
            best[n] = q
    return sorted(best.values(), key=local_value, reverse=True)[:size]


# ------------------------------------------------------------------ sessions

def sessions(df: pd.DataFrame) -> list[pd.DataFrame]:
    """Split intraday bars into sessions by local calendar date, oldest first."""
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    if df.empty:
        return []
    return [g for _, g in df.groupby(df.index.date) if len(g) >= 2]


def daily_stats(sess: list[pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for s in sess:
        rows.append({"date": s.index[0].date(), "open": float(s["Open"].iloc[0]), "high": float(s["High"].max()),
                     "low": float(s["Low"].min()), "close": float(s["Close"].iloc[-1]),
                     "value": float((s["Close"] * s["Volume"].fillna(0)).sum()), "bars": len(s)})
    d = pd.DataFrame(rows)
    d["range_pct"] = (d["high"] - d["low"]) / d["close"]
    return d


def cum_volume_at(s: pd.DataFrame, k: int) -> float:
    return float(s["Volume"].iloc[:k].fillna(0).sum())


def features(s: pd.DataFrame, k: int, prior: list[pd.DataFrame], bench_ret: float | None) -> dict | None:
    """Features after the first k bars of session s. `prior` = earlier sessions, oldest first."""
    if k < 1 or len(s) < k or len(prior) < 5:
        return None
    b = s.iloc[:k]
    o = float(b["Open"].iloc[0])
    c = float(b["Close"].iloc[-1])
    if o <= 0 or c <= 0:
        return None
    vol = b["Volume"].fillna(0)
    typ = (b["High"] + b["Low"] + b["Close"]) / 3
    vwap = float((typ * vol).sum() / vol.sum()) if vol.sum() > 0 else float(typ.mean())
    recent = prior[-20:]
    adr = float(np.mean([(p["High"].max() - p["Low"].min()) / p["Close"].iloc[-1] for p in recent]))
    past_cum = [cum_volume_at(p, k) for p in recent if len(p) >= k]
    base_cum = float(np.mean(past_cum)) if past_cum else 0.0
    rvol = cum_volume_at(s, k) / base_cum if base_cum > 0 else float("nan")
    closes = np.concatenate([[o], b["Close"].to_numpy(dtype=float)])
    path = float(np.abs(np.diff(closes)).sum())
    efficiency = abs(c - o) / path if path > 0 else 0.0
    ret = c / o - 1
    prev_close = float(prior[-1]["Close"].iloc[-1])
    orh = float(s["High"].iloc[:ORB_BARS].max()) if k >= ORB_BARS else float("nan")
    orl = float(s["Low"].iloc[:ORB_BARS].min()) if k >= ORB_BARS else float("nan")
    bar_range = float(np.median([float((p["High"] - p["Low"]).median()) for p in prior[-5:]]))
    return {
        "open": o, "price": c, "vwap": vwap, "hod": float(b["High"].max()), "lod": float(b["Low"].min()),
        "ret_open": ret, "gap": o / prev_close - 1, "prev_close": prev_close,
        "prev_high": float(prior[-1]["High"].max()), "prev_low": float(prior[-1]["Low"].min()),
        "adr_pct": adr, "rvol": rvol, "efficiency": efficiency, "orh": orh, "orl": orl,
        "rel_strength": (ret - bench_ret) if bench_ret is not None else None,
        "bar_range": bar_range, "bars": k,
    }


def score(f: dict) -> tuple[int, float, dict]:
    """(direction, signed score, component readings)."""
    side_vwap = np.sign(f["price"] - f["vwap"])
    side_move = np.sign(f["ret_open"])
    direction = int(side_vwap) if side_vwap == side_move and side_vwap != 0 else 0
    half_adr = max(f["adr_pct"] * 0.5, 1e-6)
    rv = f["rvol"]
    comp = {
        "rvol": 0.0 if not math.isfinite(rv) or rv <= 0 else float(np.clip(math.log2(rv), 0, 2) / 2),
        "efficiency": float(np.clip(f["efficiency"], 0, 1)),
        "move": float(np.clip(abs(f["ret_open"]) / half_adr, 0, 1)),
        "orb": 0.0,
        "rel_strength": 0.0,
    }
    if direction > 0 and math.isfinite(f["orh"]) and f["price"] > f["orh"]:
        comp["orb"] = 1.0
    if direction < 0 and math.isfinite(f["orl"]) and f["price"] < f["orl"]:
        comp["orb"] = 1.0
    if f["rel_strength"] is not None:
        comp["rel_strength"] = float(np.clip(direction * f["rel_strength"] / half_adr, 0, 1))
    strength = sum(WEIGHTS[k] * v for k, v in comp.items())
    return direction, direction * strength, comp


def outcome(direction: int, entry: float, exit_: float, adr_pct: float) -> int:
    """1 follow-through, -1 fade, 0 flat, for a move from entry to exit_."""
    r = direction * (exit_ / entry - 1)
    band = 0.1 * adr_pct
    return 1 if r > band else -1 if r < -band else 0


def bench_ret_at(bench_sess: dict, date, k: int) -> float | None:
    s = bench_sess.get(date)
    if s is None or len(s) < k:
        return None
    return float(s["Close"].iloc[k - 1] / s["Open"].iloc[0] - 1)


# ------------------------------------------------------------------ the scan

def decide_mode(bars_today: int, session_done: bool) -> str:
    if not session_done and bars_today >= MIN_BARS_LIVE:
        return "live"
    return "premarket"


def calibrate(hist: dict[str, list[pd.DataFrame]], bench_sess: dict, k_of, mode: str, exclude_last: bool, min_rvol: float = 0.0) -> pd.DataFrame:
    """Score every (symbol, past session) at k_of(session) bars and label the rest-of-session
    outcome. The current, unfinished session is skipped with exclude_last."""
    rows = []
    for sym, sess in hist.items():
        n = len(sess) - (1 if exclude_last else 0)
        for i in range(5, n):
            s = sess[i]
            k = k_of(s)
            if k < 1 or len(s) < k:
                continue
            f = features(s, k, sess[:i], bench_ret_at(bench_sess, s.index[0].date(), k))
            if f is None:
                continue
            d, sc, _ = score(f)
            if d == 0 or not (math.isfinite(f["rvol"]) and f["rvol"] >= min_rvol):
                continue
            if len(s) <= k:
                continue
            o = outcome(d, f["price"], float(s["Close"].iloc[-1]), f["adr_pct"])
            fwd = d * (float(s["Close"].iloc[-1]) / f["price"] - 1) / f["adr_pct"]
            rows.append({"symbol": sym, "date": s.index[0].date(), "abs_score": abs(sc), "outcome": o, "fwd_adr": fwd})
    return pd.DataFrame(rows)


def probabilities(cal: pd.DataFrame, abs_score: float) -> dict:
    if cal.empty or len(cal) < 50:
        return {"p_follow": None, "p_fade": None, "n": int(len(cal)), "note": "Too little history to calibrate."}
    base_f = float((cal["outcome"] == 1).mean())
    base_x = float((cal["outcome"] == -1).mean())
    edges = np.quantile(cal["abs_score"], [0.2, 0.4, 0.6, 0.8])
    q = int(np.searchsorted(edges, abs_score, side="right"))
    qs = np.searchsorted(edges, cal["abs_score"].to_numpy(), side="right")
    sub = cal[qs == q]
    n = len(sub)
    n_eff = min(float(n), 3.0 * sub["date"].nunique())  # stocks move together on a given day
    w = n_eff / (n_eff + SHRINK_K)
    pf = w * float((sub["outcome"] == 1).mean()) + (1 - w) * base_f if n else base_f
    px = w * float((sub["outcome"] == -1).mean()) + (1 - w) * base_x if n else base_x
    edge = pf - px
    read = ("follow-through tendency" if edge >= 0.05 else
            "fade tendency: setups this strong have more often reversed" if edge <= -0.05 else
            "no edge: follow-through and fade about equally likely")
    return {"p_follow": round(pf, 3), "p_fade": round(px, 3), "p_flat": round(1 - pf - px, 3), "edge": round(edge, 3), "read": read,
            "base_p_follow": round(base_f, 3), "quintile": q + 1, "n": n, "n_effective": round(n_eff, 1),
            "median_fwd_in_adr": round(float(sub["fwd_adr"].median()), 3) if n else None}


def plan(f: dict, direction: int, mode: str, capital: float, risk_pct: float, max_position_pct: float, square_off: str | None) -> dict:
    """Trigger-based plan, so it stays valid when data or the reader lags the market."""
    adr_abs = f["adr_pct"] * f["price"]
    atr = max(f["bar_range"], 1e-9)
    # Live plans only; pre-market plans are premarket.orb_plan.
    trigger = f["hod"] if direction > 0 else f["lod"]
    risk = max(1.5 * atr, direction * (trigger - f["vwap"]))
    extended = risk > 0.6 * adr_abs
    if extended:
        trigger = f["vwap"] + direction * 0.25 * atr
        risk = 1.5 * atr
    how = (f"Enter on a break {'above' if direction > 0 else 'below'} {trigger:.4g} (the day's {'high' if direction > 0 else 'low'})"
           if not extended else f"Extended from VWAP: wait for a pullback and hold at {trigger:.4g} near VWAP {f['vwap']:.4g}")
    stop = trigger - direction * risk
    out = {
        "side": "long" if direction > 0 else "short",
        "entry": how, "trigger": round(trigger, 4), "stop": round(stop, 4),
        "targets": [round(trigger + direction * m * risk, 4) for m in (1, 2)],
        "risk_per_share": round(risk, 4), "extended_from_vwap": extended,
        "time_stop": f"Square off by {square_off}" if square_off else "Square off before the close",
        "invalidation": f"Price closes a 5-minute bar back {'below' if direction > 0 else 'above'} VWAP",
    }
    if capital and capital > 0 and risk > 0:
        qty = math.floor(capital * risk_pct / 100 / risk)
        cap = math.floor(capital * max_position_pct / 100 / trigger)
        out["size"] = {"quantity": max(0, min(qty, cap)), "risk_pct": risk_pct, "capped": qty > cap,
                       "loss_at_stop": round(min(qty, cap) * risk, 2)}
    return out


def typical_close_time(sess: list[pd.DataFrame]) -> str | None:
    """The session's usual last bar end, observed from data rather than hard-coded."""
    ends = [s.index[-1] + timedelta(minutes=BAR_MINUTES) for s in sess[-20:]]
    if not ends:
        return None
    t = pd.Series([e.strftime("%H:%M") for e in ends]).mode().iloc[0]
    return t


def square_off_time(close_hhmm: str | None, minutes_before: int = 15) -> str | None:
    if not close_hhmm:
        return None
    t = datetime.strptime(close_hhmm, "%H:%M") - timedelta(minutes=minutes_before)
    return t.strftime("%H:%M")


def truncate_at(df: pd.DataFrame, at: datetime) -> pd.DataFrame:
    """Keep bars that had fully closed by `at` (exchange-local, tz-aware)."""
    return df[df.index + pd.Timedelta(minutes=BAR_MINUTES) <= at]
