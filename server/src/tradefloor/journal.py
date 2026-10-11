"""Decision journal: every call is logged, and every call is later scored.

A forecaster that never checks its record cannot tell skill from luck. The journal uses
transactional SQLite with explicit JSONL export; scoring grades the call once
its horizon has elapsed.
"""

from __future__ import annotations

import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import events, paper, settings, storage, validation

REQUIRED = ("symbol", "as_of", "horizon_days", "price", "direction", "p_up", "p_down")
REQUIRED_INTRADAY = ("symbol", "exchange", "mode", "direction")
REQUIRED_LIVE = ("trigger", "stop", "targets")


def journal_path() -> Path:
    # One journal for every agent host, so the track record follows the user, not the tool.
    return settings.home() / "journal.jsonl"


def record(entry: dict) -> dict:
    if not isinstance(entry, dict):
        raise ValueError("entry must be an object")
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
    e["symbol"] = validation.symbol(e["symbol"])
    if intraday:
        from . import markets
        if e["exchange"] not in markets.EXCHANGES or e["mode"] not in ("live", "premarket"):
            raise ValueError("invalid intraday exchange or mode")
        e["direction"] = validation.direction(e["direction"], ("LONG", "SHORT") if e["mode"] == "live" else ("EITHER", "LONG", "SHORT"))
        if e["mode"] == "live":
            datetime.strptime(e["signal_time"], "%Y-%m-%d %H:%M")
            trig = validation.number(e["trigger"], "trigger", 1e-12)
            stop = validation.number(e["stop"], "stop", 1e-12)
            d = 1 if e["direction"] == "LONG" else -1
            if d * (trig - stop) <= 0 or not e["targets"]:
                raise ValueError("stop must be on the risk side; targets cannot be empty")
            for target in e["targets"]:
                if d * (validation.number(target, "target", 1e-12) - trig) <= 0:
                    raise ValueError("target must be on the profit side")
            for field in ("p_follow", "p_win"):
                if e.get(field) is not None:
                    validation.number(e[field], field, 0, 1)
            if e.get("signal_price") is not None:
                validation.number(e["signal_price"], "signal_price", 1e-12)
                validation.number(e.get("adr_pct"), "adr_pct", 1e-12, 10)
        else:
            e["target_session"] = validation.iso_date(e["target_session"], "target_session")
            validation.number(e["adr_pct"], "adr_pct", 1e-12, 10)
            validation.number(e["prev_close"], "prev_close", 1e-12)
            if e.get("p_big_move") is not None:
                validation.number(e["p_big_move"], "p_big_move", 0, 1)
    else:
        e["direction"] = validation.direction(e["direction"])
        e["as_of"] = validation.iso_date(e["as_of"], "as_of")
        e["horizon_days"] = validation.integer(e["horizon_days"], "horizon_days")
        e["price"] = validation.number(e["price"], "price", 1e-12)
        probs = validation.probabilities({"up": e["p_up"], "down": e["p_down"],
                                         "flat": e.get("p_flat", 1 - float(e["p_up"]) - float(e["p_down"]))})
        e.update(p_up=probs["up"], p_down=probs["down"], p_flat=probs["flat"])
        e["event_contract"] = events.for_entry(e)
        if e.get("base_p_up") is not None:
            validation.number(e["base_p_up"], "base_p_up", 0, 1)
        if e.get("base_probabilities") is not None:
            e["base_probabilities"] = validation.probabilities(e["base_probabilities"])
        if e.get("source") == "full":
            check = validation.decision(e.get("quant_prior"), probs, e.get("evidence", []), e.get("adjustments", []))
            if check["direction"] != e["direction"]:
                raise ValueError("decision direction disagrees with probabilities")
            e["decision_validation"] = check
        if e.get("stop") is not None:
            validation.number(e["stop"], "stop", 1e-12)
            d = 1 if e["direction"] == "UP" else -1 if e["direction"] == "DOWN" else 0
            if d and d * (e["price"] - float(e["stop"])) <= 0:
                raise ValueError("daily stop must be on the risk side")
        for target in e.get("targets") or []:
            value = validation.number(target, "target", 1e-12)
            if e["direction"] in ("UP", "DOWN") and (value-e["price"])*(1 if e["direction"]=="UP" else -1) <= 0:
                raise ValueError("daily targets must be on the profit side")
    e.setdefault("id", uuid.uuid4().hex[:12])
    if not isinstance(e["id"], str) or not e["id"] or len(e["id"]) > 128:
        raise ValueError("invalid journal ID")
    e["recorded_at"] = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    e["registration_timing"] = "historical" if e.get("as_of", e["recorded_at"][:10]) < e["recorded_at"][:10] else "same-day; availability not independently verified"
    for field in ("cost_bps", "slippage_bps"):
        if e.get(field) is not None:
            validation.number(e[field], field, 0, 1000)
    # Materialize legacy entries before adding a new one; never discard corrupt input.
    load()
    with storage.connect(settings.home() / "journal.sqlite3") as db:
        db.execute("INSERT INTO records(id,body) VALUES (?,?)", (e["id"], storage.canonical(e)))
    return e


def load() -> list[dict]:
    with storage.connect(settings.home() / "journal.sqlite3") as db:
        if not db.execute("SELECT 1 FROM metadata WHERE key='jsonl_imported'").fetchone():
            p = journal_path()
            if p.exists():
                for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                    if not line.strip():
                        continue
                    try:
                        e = json.loads(line, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
                        if not isinstance(e, dict) or "symbol" not in e:
                            raise ValueError("not a journal entry")
                        e.setdefault("id", f"legacy-{n}")
                        db.execute("INSERT INTO records(id,body) VALUES (?,?)", (e["id"], storage.canonical(e)))
                    except (ValueError, TypeError) as ex:
                        raise ValueError(f"Journal corruption at {p}, line {n}: {ex}; original file preserved") from ex
            db.execute("INSERT INTO metadata(key,value) VALUES ('jsonl_imported','1')")
        return [json.loads(row[0]) for row in db.execute("SELECT body FROM records ORDER BY seq")]


def export() -> dict:
    """Explicit interoperable export; atomic replace of the derived JSONL file."""
    import os
    import tempfile
    entries = load()
    fd, tmp = tempfile.mkstemp(dir=settings.home(), prefix="journal-export-", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(storage.canonical(e) + "\n")
    os.replace(tmp, journal_path())
    return {"entries": len(entries), "path": str(journal_path())}


def score_entry(entry: dict, after: pd.DataFrame) -> dict:
    """Grade one call. `after` holds bars strictly after entry['as_of'], oldest first."""
    h = int(entry["horizon_days"])
    base = {"id": entry.get("id"), "symbol": entry["symbol"], "as_of": entry["as_of"], "direction": entry["direction"], "horizon_days": h}
    if len(after) < h:
        return {**base, "status": "open", "bars_elapsed": int(len(after))}
    window = after.iloc[:h]
    price = float(entry["price"])
    end = validation.number(window["Close"].iloc[-1], "settlement.close", 1e-12)
    ret = end / price - 1
    event = events.for_entry(entry)
    value = math.log(end / price) if event["return_convention"] == "log" else ret
    outcome = events.label(value, event["flat_band"])
    p = {"up": entry["p_up"], "down": entry["p_down"], "flat": entry.get("p_flat", 1 - entry["p_up"] - entry["p_down"])}
    scores = events.score(p, outcome)
    res = {**base, "status": "scored", "realized_return_pct": round(ret * 100, 2), "outcome": outcome,
           "realized_return": ret, "hit": outcome == entry["direction"], **scores,
           "event_version": event["version"], "adjustment_method": after.attrs.get("adjustment_method", "caller must supply matching price basis")}
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
        return {"scored": 0, "open": sum(s["status"] == "open" for s in scored),
                "errors": sum(s["status"] != "open" for s in scored), "note": "No scored outcomes; inspect open/error statuses."}
    by_id = {e.get("id"): e for e in entries}
    hits = np.mean([s["hit"] for s in done])
    brier = np.mean([s["brier_up"] for s in done])
    # Reference: always forecasting the base rate each entry carried. Beating it is the bar.
    ref, paired, multi_ref, multi_pair = [], [], [], []
    for s in done:
        e = by_id.get(s["id"], {})
        b = e.get("base_p_up")
        if b is not None:
            ref.append((float(b) - float(s["outcome"] == "UP")) ** 2)
            paired.append(s["brier_up"])
        if e.get("base_probabilities") and "brier_multiclass" in s:
            multi_ref.append(events.score(e["base_probabilities"], s["outcome"])["brier_multiclass"])
            multi_pair.append(s["brier_multiclass"])
    out = {
        "scored": len(done),
        "open": sum(s["status"] == "open" for s in scored),
        "errors": sum(s["status"] not in ("open", "scored") for s in scored),
        "hit_rate": round(float(hits), 3),
        "brier_up": round(float(brier), 4),
        "mean_realized_return_pct_when_up_call": _mean([s["realized_return_pct"] for s in done if s["direction"] == "UP"]),
        "mean_realized_return_pct_when_down_call": _mean([s["realized_return_pct"] for s in done if s["direction"] == "DOWN"]),
    }
    if ref:
        out["brier_base_rate_reference"] = round(float(np.mean(ref)), 4)
        out["brier_up_paired"] = round(float(np.mean(paired)), 4)
        out["reference_pairs"] = len(ref)
        out["reference_excluded"] = len(done) - len(ref)
        out["beats_base_rate"] = bool(np.mean(paired) < np.mean(ref))
    if multi_ref:
        out["brier_multiclass_paired"] = float(np.mean(multi_pair))
        out["brier_multiclass_reference"] = float(np.mean(multi_ref))
        out["brier_skill"] = 1 - float(np.mean(multi_pair)) / float(np.mean(multi_ref)) if np.mean(multi_ref) > 0 else None
    by_source = {}
    for s in done:
        src = by_id.get(s["id"], {}).get("source", "unknown")
        by_source.setdefault(src, []).append(s)
    if len(by_source) > 1:
        out["by_source"] = {src: {"scored": len(v), "hit_rate": round(float(np.mean([x["hit"] for x in v])), 3),
                                  "brier_up": round(float(np.mean([x["brier_up"] for x in v])), 4)} for src, v in by_source.items()}
    versions = {s.get("event_version", "legacy") for s in done}
    out["by_event_version"] = {v: {"scored": sum(s.get("event_version", "legacy") == v for s in done),
                                   "brier_up": float(np.mean([s["brier_up"] for s in done if s.get("event_version", "legacy") == v]))} for v in versions}
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
    result = {**base, **paper.trade(session, d, trig, stop, t1, complete, entry.get("cost_bps", 0),
                                    entry.get("slippage_bps", 0), entry.get("square_off"), entry.get("entry_style", "breakout"))}
    if entry.get("p_win") is not None and result.get("triggered") and result["status"] == "scored":
        result["brier_win"] = (float(entry["p_win"]) - float(result["hit"])) ** 2
    # Continuation is measured at the actual close, independently of paper-trade exit.
    if complete and entry.get("p_follow") is not None and entry.get("signal_price") and entry.get("adr_pct"):
        signed_return = d * (float(session["Close"].iloc[-1]) / float(entry["signal_price"]) - 1)
        follow = signed_return > 0.1 * float(entry["adr_pct"])
        result.update(forecast_follow=follow, brier_follow=(float(entry["p_follow"]) - float(follow)) ** 2)
    else:
        result["forecast_scoring"] = "unavailable until session closes with signal_price and adr_pct; paper win is a different event"
    return result


def summarize_intraday(scored: list[dict]) -> dict | None:
    done = [s for s in scored if s.get("kind") == "intraday" and s["status"] == "scored"]
    if not done:
        return None
    trig = [s for s in done if s.get("triggered")]
    out = {"scored": len(done), "triggered": len(trig)}
    follow = [s for s in done if "brier_follow" in s]
    if follow:
        out["continuation_scored"] = len(follow)
        out["brier_follow"] = float(np.mean([s["brier_follow"] for s in follow]))
        out["continuation_note"] = "Session-close forecast outcome, separate from conditional paper wins"
    pre = [s for s in done if "big_move" in s]
    if pre:
        out["premarket_big_move_rate"] = round(float(np.mean([s["big_move"] for s in pre])), 3)
        graded = [s["brier_big_move"] for s in pre if "brier_big_move" in s]
        out["premarket_brier_big_move"] = round(float(np.mean(graded)), 4) if graded else None
    if trig:
        out["win_rate"] = round(float(np.mean([s["hit"] for s in trig])), 3)
        out["avg_r"] = round(float(np.mean([s["r_multiple"] for s in trig])), 2)
        out["total_r"] = round(float(np.sum([s["r_multiple"] for s in trig])), 2)
    if len(trig) < 30:
        out["note"] = f"Only {len(trig)} triggered intraday calls. Under ~30 the win rate is mostly noise."
    return out
