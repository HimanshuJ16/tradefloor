"""Decision journal: every call is logged, and every call is later scored.

A forecaster that never checks its record cannot tell skill from luck. The journal is
append-only JSONL; scoring reads prices after each entry's as_of and grades the call once
its horizon has elapsed.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import settings

REQUIRED = ("symbol", "as_of", "horizon_days", "price", "direction", "p_up", "p_down")
REQUIRED_INTRADAY = ("symbol", "exchange", "mode", "direction")
REQUIRED_LIVE = ("trigger", "stop", "targets")


def journal_path() -> Path:
    # One journal for every agent host, so the track record follows the user, not the tool.
    return settings.home() / "journal.jsonl"


def record(entry: dict) -> dict:
    intraday = entry.get("kind") == "intraday"
    missing = [k for k in (REQUIRED_INTRADAY if intraday else REQUIRED) if entry.get(k) is None]
    if intraday:
        if entry.get("mode") == "live":
            missing += [k for k in REQUIRED_LIVE if entry.get(k) is None]
            if not entry.get("signal_time"):
                missing.append("signal_time (YYYY-MM-DD HH:MM, exchange time)")
        if entry.get("mode") == "premarket":
            missing += [k for k in ("target_session", "adr_pct", "prev_close") if entry.get(k) is None]
    if missing:
        raise ValueError(f"journal entry missing: {', '.join(missing)}")
    e = dict(entry)
    e["direction"] = str(e["direction"]).upper()
    e.setdefault("id", uuid.uuid4().hex[:12])
    e.setdefault("recorded_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    with journal_path().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    return e


def load() -> list[dict]:
    p = journal_path()
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def score_entry(entry: dict, after: pd.DataFrame) -> dict:
    """Grade one call. `after` holds bars strictly after entry['as_of'], oldest first."""
    h = int(entry["horizon_days"])
    base = {"id": entry.get("id"), "symbol": entry["symbol"], "as_of": entry["as_of"], "direction": entry["direction"], "horizon_days": h}
    if len(after) < h:
        return {**base, "status": "open", "bars_elapsed": int(len(after))}
    window = after.iloc[:h]
    price = float(entry["price"])
    end = float(window["Close"].iloc[-1])
    ret = end / price - 1
    band = float(entry.get("flat_band_pct", 0) or 0) / 100
    outcome = "UP" if ret > band else "DOWN" if ret < -band else "SIDEWAYS"
    p_up = float(entry["p_up"])
    brier = (p_up - (1.0 if ret > 0 else 0.0)) ** 2
    res = {**base, "status": "scored", "realized_return_pct": round(ret * 100, 2), "outcome": outcome,
           "hit": outcome == entry["direction"], "brier_up": round(brier, 4)}
    stop = entry.get("stop")
    if stop is not None:
        stop = float(stop)
        if entry["direction"] == "UP":
            res["stop_hit"] = bool((window["Low"] <= stop).any())
        elif entry["direction"] == "DOWN":
            res["stop_hit"] = bool((window["High"] >= stop).any())
    return res


def summarize(scored: list[dict], entries: list[dict]) -> dict:
    done = [s for s in scored if s["status"] == "scored"]
    if not done:
        return {"scored": 0, "open": len(scored), "note": "No call has reached its horizon yet."}
    by_id = {e.get("id"): e for e in entries}
    hits = np.mean([s["hit"] for s in done])
    brier = np.mean([s["brier_up"] for s in done])
    # Reference: always forecasting the base rate each entry carried. Beating it is the bar.
    ref = []
    for s in done:
        e = by_id.get(s["id"], {})
        b = e.get("base_p_up")
        if b is not None:
            ref.append((float(b) - (1.0 if s["realized_return_pct"] > 0 else 0.0)) ** 2)
    out = {
        "scored": len(done),
        "open": len(scored) - len(done),
        "hit_rate": round(float(hits), 3),
        "brier_up": round(float(brier), 4),
        "mean_realized_return_pct_when_up_call": _mean([s["realized_return_pct"] for s in done if s["direction"] == "UP"]),
        "mean_realized_return_pct_when_down_call": _mean([s["realized_return_pct"] for s in done if s["direction"] == "DOWN"]),
    }
    if ref:
        out["brier_base_rate_reference"] = round(float(np.mean(ref)), 4)
        out["beats_base_rate"] = bool(brier < np.mean(ref))
    by_source = {}
    for s in done:
        src = by_id.get(s["id"], {}).get("source", "unknown")
        by_source.setdefault(src, []).append(s)
    if len(by_source) > 1:
        out["by_source"] = {src: {"scored": len(v), "hit_rate": round(float(np.mean([x["hit"] for x in v])), 3),
                                  "brier_up": round(float(np.mean([x["brier_up"] for x in v])), 4)} for src, v in by_source.items()}
    if len(done) < 30:
        out["note"] = f"Only {len(done)} scored calls. Under ~30 the hit rate is mostly noise."
    return out


def _mean(xs: list[float]):
    return round(float(np.mean(xs)), 2) if xs else None


def score_intraday(entry: dict, session: pd.DataFrame, complete: bool) -> dict:
    """Grade an intraday call on the 5-minute bars of the session it was meant for.

    `session` holds that session's bars from the moment the call became valid (after the
    signal time for a live call; after the opening range for a next-session call).
    Triggered when price reaches the trigger; then the first of stop or first target wins,
    with a bar that touches both counted as the stop. Untouched trades exit at the close.
    """
    base = {"id": entry.get("id"), "symbol": entry["symbol"], "kind": "intraday", "session": entry.get("session_date"),
            "direction": entry["direction"]}
    if session.empty:
        return {**base, "status": "open" if not complete else "no data"}
    d = 1 if entry["direction"] in ("LONG", "UP") else -1
    trig, stop = float(entry["trigger"]), float(entry["stop"])
    t1 = float(entry["targets"][0])
    risk = abs(trig - stop)
    hit_trigger = session["High"] >= trig if d > 0 else session["Low"] <= trig
    if not hit_trigger.any():
        if not complete:
            return {**base, "status": "open"}
        return {**base, "status": "scored", "triggered": False, "r_multiple": 0.0, "hit": None}
    after = session.loc[hit_trigger.idxmax():]
    stop_hit = after["Low"] <= stop if d > 0 else after["High"] >= stop
    tgt_hit = after["High"] >= t1 if d > 0 else after["Low"] <= t1
    first_stop = stop_hit.idxmax() if stop_hit.any() else None
    first_tgt = tgt_hit.idxmax() if tgt_hit.any() else None
    if first_stop is not None and (first_tgt is None or first_stop <= first_tgt):
        r, exit_how = -1.0, "stop"
    elif first_tgt is not None:
        r, exit_how = abs(t1 - trig) / risk, "target 1"
    elif complete:
        r, exit_how = d * (float(after["Close"].iloc[-1]) - trig) / risk, "close"
    else:
        return {**base, "status": "open", "triggered": True}
    return {**base, "status": "scored", "triggered": True, "exit": exit_how, "r_multiple": round(r, 2), "hit": r > 0,
            "brier_follow": round((float(entry.get("p_follow") or 0.5) - (1.0 if r > 0 else 0.0)) ** 2, 4)}


def summarize_intraday(scored: list[dict]) -> dict | None:
    done = [s for s in scored if s.get("kind") == "intraday" and s["status"] == "scored"]
    if not done:
        return None
    trig = [s for s in done if s.get("triggered")]
    out = {"scored": len(done), "triggered": len(trig)}
    pre = [s for s in done if "big_move" in s]
    if pre:
        out["premarket_big_move_rate"] = round(float(np.mean([s["big_move"] for s in pre])), 3)
        out["premarket_brier_big_move"] = round(float(np.mean([s["brier_big_move"] for s in pre])), 4)
    if trig:
        out["win_rate"] = round(float(np.mean([s["hit"] for s in trig])), 3)
        out["avg_r"] = round(float(np.mean([s["r_multiple"] for s in trig])), 2)
        out["total_r"] = round(float(np.sum([s["r_multiple"] for s in trig])), 2)
    if len(trig) < 30:
        out["note"] = f"Only {len(trig)} triggered intraday calls. Under ~30 the win rate is mostly noise."
    return out
