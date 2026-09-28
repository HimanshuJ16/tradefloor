"""Orchestrates an intraday momentum scan over a market's universe. See intraday.py for
the method; this module does the fetching, point-in-time cutting, and assembly."""

from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import data, intraday as it, markets, premarket as pm, settings


def _custom_list(market: str) -> list[str] | None:
    parts = [p.strip().upper() for p in re.split(r"[,\s]+", market) if p.strip()]
    if len(parts) >= 2 and all(re.fullmatch(r"\^?[A-Z0-9.\-=&]{1,20}", p) for p in parts):
        return parts
    return None


def build_universe(market: str, size: int | None) -> dict:
    custom = None if it.resolve_universe(market) else _custom_list(market)
    if custom:
        code = markets.exchange_for_symbol(custom[0])
        return {"symbols": custom[:150], "exchange": code, "label": f"custom list of {len(custom)} symbols",
                "region": None, "delay_minutes": None}
    spec = it.resolve_universe(market)
    if spec is None:
        raise LookupError(f"Unknown market {market!r}. Known: {', '.join(sorted(it.UNIVERSES))}. "
                          "Or pass two or more symbols separated by commas.")
    n = min(150, size or spec.size)
    pages = 1 if spec.region in ("us", "in", "jp", "kr", "cn", "tw", "hk", "sa", "au") else 3
    quotes = it.filter_home_listings(data.screen(spec.region, spec.exchanges, pages, spec.sector), n)
    if not quotes:
        raise LookupError(f"The screener returned no {spec.region.upper()} listings for {market!r}.")
    delays = Counter(int(q.get("exchangeDataDelayedBy") or 0) for q in quotes)
    return {"symbols": [q["symbol"] for q in quotes], "exchange": spec.exchange_code, "label": spec.label,
            "region": spec.region, "delay_minutes": delays.most_common(1)[0][0],
            "earnings": {q["symbol"]: d for q in quotes if (d := _earnings_date(q))}}


def _earnings_date(q: dict) -> date | None:
    ts = q.get("earningsTimestamp")
    if not ts:
        return None
    tz = ZoneInfo(q.get("exchangeTimezoneName") or "UTC")
    return datetime.fromtimestamp(int(ts), tz).date()


def parse_at(at: str | None, tz: ZoneInfo) -> datetime | None:
    if not at:
        return None
    d = datetime.strptime(at.strip()[:16], "%Y-%m-%d %H:%M")
    return d.replace(tzinfo=tz)


def run(market: str, top: int = 8, at: str | None = None, size: int | None = None, side: str = "both",
        min_rvol: float = 0.8, mode: str = "auto") -> dict:
    uni = build_universe(market, size)
    ex = markets.EXCHANGES[uni["exchange"]]
    tz = ZoneInfo(ex.tz)
    bench_sym = ex.benchmark if ex.benchmark and ex.benchmark not in uni["symbols"] else None
    bars = data.intraday_bars(uni["symbols"] + ([bench_sym] if bench_sym else []), tz=ex.tz)
    at_dt = parse_at(at, tz)
    now = at_dt or datetime.now(tz)
    if at_dt:
        bars = {s: it.truncate_at(df, at_dt) for s, df in bars.items()}
    hist = {s: it.sessions(df) for s, df in bars.items() if s != bench_sym}
    hist = {s: v for s, v in hist.items() if len(v) >= 8}
    if not hist:
        raise LookupError("No intraday history came back for this universe.")
    bench_sess = {s.index[0].date(): s for s in it.sessions(bars.get(bench_sym, pd.DataFrame()))} if bench_sym else {}

    ref = max(hist.values(), key=len)
    close_hhmm = it.typical_close_time(ref)
    last = ref[-1]
    today = now.date()
    session_done = last.index[0].date() < today or (close_hhmm is not None and now.strftime("%H:%M") >= close_hhmm)
    bars_today = len(last) if last.index[0].date() == today else 0
    live_possible = it.decide_mode(bars_today, session_done) == "live"
    if mode == "live" and not live_possible:
        raise LookupError("The session is not open with at least 15 minutes of bars, so there is nothing live to scan. "
                          "Run without mode='live' for the pre-market watchlist.")
    if mode == "premarket" or (mode == "auto" and not live_possible):
        return _premarket(market, uni, ex, hist, now, today, close_hhmm, top, side, at)
    mode = "live"
    k_live = bars_today
    cal = it.calibrate(hist, bench_sess, lambda s: k_live, "live", exclude_last=True, min_rvol=min_rvol)

    rows, above_vwap, total = [], 0, 0
    values = {s: float(np.median(it.daily_stats(v[-21:-1])["value"])) for s, v in hist.items()}
    liq_floor = float(np.quantile(list(values.values()), 0.3)) if len(values) >= 5 else 0.0
    for sym, sess in hist.items():
        cur = sess[-1]
        if cur.index[0].date() != today:
            continue  # no bars today for this symbol: halted, holiday, or not yet trading
        k = min(len(cur), k_live)
        f = it.features(cur, k, sess[:-1], it.bench_ret_at(bench_sess, cur.index[0].date(), k))
        if f is None:
            continue
        total += 1
        above_vwap += f["price"] > f["vwap"]
        d, sc, comp = it.score(f)
        if d == 0 or values[sym] < liq_floor or f["adr_pct"] < 0.008 or not (np.isfinite(f["rvol"]) and f["rvol"] >= min_rvol):
            continue
        if side == "long" and d < 0 or side == "short" and d > 0:
            continue
        rows.append((sym, d, sc, comp, f))

    rows.sort(key=lambda r: -abs(r[2]))
    s = settings.effective()
    cap = s["capital"]["value"]
    risk = s["intraday_risk_pct"]["value"]
    maxpos = s["max_position_pct"]["value"]
    sq = it.square_off_time(close_hhmm)
    cands = []
    for sym, d, sc, comp, f in rows[:top]:
        pr = it.probabilities(cal, abs(sc))
        c = {
            "symbol": sym, "direction": "LONG" if d > 0 else "SHORT", "score": round(sc, 3),
            "components": {k: round(v, 2) for k, v in comp.items()},
            "price": round(f["price"], 4), "vwap": round(f["vwap"], 4), "move_since_open_pct": round(f["ret_open"] * 100, 2),
            "gap_pct": round(f["gap"] * 100, 2), "rvol": None if not np.isfinite(f["rvol"]) else round(f["rvol"], 2),
            "efficiency": round(f["efficiency"], 2), "adr_pct": round(f["adr_pct"] * 100, 2),
            "rel_strength_vs_index_pct": None if f["rel_strength"] is None else round(f["rel_strength"] * 100, 2),
            "day_high": round(f["hod"], 4), "day_low": round(f["lod"], 4), "prev_high": round(f["prev_high"], 4), "prev_low": round(f["prev_low"], 4),
            "probabilities": pr,
            "plan": it.plan(f, d, mode, cap, risk, maxpos, sq),
        }
        if uni.get("earnings", {}).get(sym) == today:
            c["event"] = "Earnings scheduled today"
        cands.append(c)

    last_bar_end = (last.index[-1] + pd.Timedelta(minutes=it.BAR_MINUTES))
    out = {
        "market": market, "universe": uni["label"], "universe_size": len(hist), "exchange": ex.code, "currency": ex.currency,
        "mode": mode,
        "as_of": now.strftime("%Y-%m-%d %H:%M %Z"),
        "session_date": str(last.index[0].date()),
        "bars_into_session": k_live,
        "last_bar_end": last_bar_end.strftime("%Y-%m-%d %H:%M"),
        "data_age_minutes": round((now - last_bar_end).total_seconds() / 60, 1),
        "exchange_delay_minutes": uni["delay_minutes"],
        "session_close": close_hhmm, "square_off_by": sq,
        "breadth": {"scored": total, "pct_above_vwap": round(100 * above_vwap / total, 1) if total else None,
                    "index_move_pct": _index_move(bench_sess, last.index[0].date(), k_live)},
        "calibration": {"samples": int(len(cal)), "sessions": int(cal["date"].nunique()) if len(cal) else 0,
                        "outcome": "rest of session from the scan time",
                        "base_p_follow": round(float((cal["outcome"] == 1).mean()), 3) if len(cal) else None},
        "filters": {"min_rvol": min_rvol, "min_adr_pct": 0.8, "liquidity": "top 70% of the universe by traded value"},
        "candidates": cands,
        "regime_read": _regime_read(cal),
        "market_note": it.MARKET_NOTES.get(uni["region"] or ""),
        "caveats": [
            "Probabilities are how often setups of the same strength followed through in this universe over the past sessions of 5-minute data, not a promise.",
            "Plans are trigger-based: act only if price reaches the trigger, so a delayed read does not become a stale market order.",
            "Yahoo intraday data can be delayed; check exchange_delay_minutes and data_age_minutes before acting.",
        ],
        "disclaimer": "Not investment advice. Public data, possibly delayed; verify before acting.",
    }
    if at_dt:
        out["replay"] = f"Point-in-time replay: only bars closed by {at} were used."
    return out


def _next_weekday(d: date) -> date:
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _premarket(market, uni, ex, hist, now, today, close_hhmm, top, side, at) -> dict:
    """Watchlist for the coming session: stocks likely to make a big move, two-sided plans."""
    # A partial session already started today is not "before" the target: drop it.
    started_today = {s: v[-1].index[0].date() == today for s, v in hist.items()}
    prior = {s: (v[:-1] if started_today[s] else v) for s, v in hist.items()}
    last_date = max(v[-1].index[0].date() for v in prior.values())
    target = today if (any(started_today.values()) or (today > last_date and today.weekday() < 5)) else _next_weekday(last_date)

    pool = pm.history(prior)
    if len(pool) < 100:
        raise LookupError("Too little history to calibrate the pre-market model for this universe.")
    scorer = pm.InPlayScorer(pool)
    values = {s: float(np.median(it.daily_stats(v[-20:])["value"])) for s, v in prior.items()}
    liq_floor = float(np.quantile(list(values.values()), 0.3)) if len(values) >= 5 else 0.0

    st = settings.effective()
    sq = it.square_off_time(close_hhmm)
    rows = []
    for sym, sess in prior.items():
        f = pm.features_before(sess)
        if f is None or values[sym] < liq_floor or f["adr_pct"] < 0.008:
            continue
        pr = pm.probabilities(pool, scorer, f)
        if pr.get("p_big_move") is None:
            continue
        lean = pr["direction"].get("side")
        if side in ("long", "short") and lean and lean.lower() != side:
            continue
        rows.append((sym, f, pr, lean))
    earnings = uni.get("earnings", {})
    rows.sort(key=lambda r: (earnings.get(r[0]) == target, r[2]["in_play_score"]), reverse=True)

    cands = []
    for sym, f, pr, lean in rows[:top]:
        c = {
            "symbol": sym,
            "p_big_move": pr["p_big_move"], "lift_vs_universe": pr["lift"], "p_trend_day": pr["p_trend_day"],
            "direction": pr["direction"],
            "yesterday": {"session": str(f["session_date"]), "move_pct": round(f["prev_ret"] * 100, 2),
                          "close_location": round(f["prev_close_loc"], 2),
                          "traded_value_vs_avg": round(f["value_ratio"], 2), "range_vs_avg": round(f["range_ratio"], 2)},
            "adr_pct": round(f["adr_pct"] * 100, 2),
            "probabilities": pr,
            "plan": pm.orb_plan(f, lean, st["capital"]["value"], st["intraday_risk_pct"]["value"], st["max_position_pct"]["value"], sq),
        }
        if earnings.get(sym) == target:
            c["event"] = f"Earnings scheduled on {target}: expect a large move, and a gap that can skip the stop"
        cands.append(c)

    scores = scorer.pool_scores
    top_q = pool[scores >= np.quantile(scores, 0.8)]
    base = float(pool["big_move"].mean())
    top_rate = float(top_q["big_move"].mean())
    strong = pool[pool["strong_prev"] & pool["same_dir"].notna()]
    cont = float(strong["same_dir"].astype(float).mean()) if len(strong) else None
    read = (f"Stocks in play yesterday (top fifth) had big moves {top_rate:.0%} of sessions, against {base:.0%} for the universe."
            + (f" After strong days the next day continued {cont:.0%} of the time, so the side is decided at the open unless a lean is shown." if cont is not None else ""))
    out = {
        "market": market, "universe": uni["label"], "universe_size": len(prior), "exchange": ex.code, "currency": ex.currency,
        "mode": "premarket",
        "as_of": now.strftime("%Y-%m-%d %H:%M %Z"),
        "target_session": str(target) + ("" if target == today else " (next weekday; exchange holidays not checked)"),
        "based_on_session": str(last_date),
        "session_close": close_hhmm, "square_off_by": sq,
        "exchange_delay_minutes": uni["delay_minutes"],
        "evidence": {
            "sessions": int(pool["date"].nunique()), "stock_days": int(len(pool)),
            "big_move_definition": f"high-low range at least {pm.BIG_MOVE_X_ADR}x the stock's 20-session average range",
            "base_p_big_move": round(base, 3), "top_fifth_in_play_p_big_move": round(top_rate, 3),
            "strong_day_continuation_rate": None if cont is None else round(cont, 3),
            "read": read,
        },
        "candidates": cands,
        "market_note": it.MARKET_NOTES.get(uni["region"] or ""),
        "next_step": "After the first 15 minutes of the session, run the live scan (same command) to see which side broke, with volume and VWAP.",
        "caveats": [
            "p_big_move is how often stocks this in-play had a big move in this universe over the past sessions; it says nothing about direction.",
            "Pre-market gaps are not seen here (Yahoo has no pre-open data for most exchanges); a large gap changes the plan.",
            "Exchange holidays are not checked.",
        ],
        "disclaimer": "Not investment advice. Public data, possibly delayed; verify before acting.",
    }
    if any(started_today.values()):
        out["note"] = "The session has started but the 15-minute opening range is not complete; this is the pre-market view. Re-run after 15 minutes for the live scan."
    if at:
        out["replay"] = f"Point-in-time replay: only bars closed by {at} were used."
    return out


def _regime_read(cal: pd.DataFrame) -> str | None:
    """How momentum has behaved in this universe lately, at the strongest quintile."""
    if cal.empty or len(cal) < 50:
        return None
    top = cal[cal["abs_score"] >= cal["abs_score"].quantile(0.8)]
    f, x = float((top["outcome"] == 1).mean()), float((top["outcome"] == -1).mean())
    if f - x >= 0.05:
        return f"Momentum has persisted lately: the strongest setups followed through {f:.0%} of the time and faded {x:.0%}."
    if x - f >= 0.05:
        return f"Momentum has reversed lately: the strongest setups faded {x:.0%} of the time and followed through {f:.0%}. Treat momentum entries with suspicion; fades or no trade may be the better read."
    return f"No momentum edge lately: the strongest setups followed through {f:.0%} and faded {x:.0%}."


def _index_move(bench_sess: dict, date, k: int | None) -> float | None:
    s = bench_sess.get(date)
    if s is None:
        return None
    k = len(s) if k is None else min(k, len(s))
    return round(float(s["Close"].iloc[k - 1] / s["Open"].iloc[0] - 1) * 100, 2)
