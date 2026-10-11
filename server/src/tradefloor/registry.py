"""Append-only prospective experiment status and settlements, exported without raw data."""

from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from . import evaluation, settings, storage, validation


def record(experiment: dict) -> dict:
    status = experiment.get("status")
    if status not in ("forecast", "abstained", "failed"):
        raise ValueError("experiment status must be forecast, abstained or failed")
    e = {
        **experiment,
        "id": uuid.uuid4().hex,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    validation.iso_date(e["as_of"], "as_of")
    validation.symbol(e["symbol"])
    if not e.get("source") or not e.get("experiment_key"):
        raise ValueError("source and experiment_key are required")
    if status == "forecast":
        e["probabilities"] = validation.probabilities(e["probabilities"])
        e["reference"] = validation.probabilities(e["reference"])
        from . import events

        events.validate(e["event_contract"])
        if e["event_contract"]["as_of"] != e["as_of"]:
            raise ValueError("experiment date disagrees with event contract")
    e["registration_timing"] = (
        "historical"
        if e["as_of"] < e["recorded_at"][:10]
        else "same-day; event availability not independently verified"
    )
    with storage.connect(settings.home() / "experiments.sqlite3") as db:
        if db.execute(
            "SELECT 1 FROM records WHERE json_extract(body,'$.experiment_key')=? AND json_extract(body,'$.source')=?",
            (e["experiment_key"], e["source"]),
        ).fetchone():
            raise ValueError("this experiment/source is already registered")
        from . import runs

        previous = db.execute(
            "SELECT body FROM records ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        e["previous_commitment"] = (
            json.loads(previous[0])["commitment"] if previous else None
        )
        e["commitment"] = runs.digest(e)
        db.execute(
            "INSERT INTO records(id,body) VALUES (?,?)", (e["id"], storage.canonical(e))
        )
    return e


def settle(
    identifier: str,
    outcome: str,
    method: str | None = None,
    label_end: str | None = None,
) -> dict:
    if outcome not in ("UP", "DOWN", "SIDEWAYS"):
        raise ValueError("outcome must be UP, DOWN or SIDEWAYS")
    with storage.connect(settings.home() / "experiments.sqlite3") as db:
        row = db.execute(
            "SELECT body FROM records WHERE id=?", (identifier,)
        ).fetchone()
        if not row:
            raise ValueError("unknown experiment")
        e = json.loads(row[0])
        if e["status"] != "forecast":
            raise ValueError("only forecasts can be settled")
        s = {
            "id": identifier,
            "outcome": outcome,
            "settled_at": datetime.now(timezone.utc).isoformat(),
            "method": method
            or "caller-supplied outcome; use the forecast's event contract; not independently verified",
            "label_end": validation.iso_date(label_end) if label_end else None,
        }
        db.execute(
            "INSERT INTO settlements(id,body) VALUES (?,?)",
            (identifier, storage.canonical(s)),
        )
    return s


def scoreboard() -> dict:
    with storage.connect(settings.home() / "experiments.sqlite3") as db:
        entries = [
            json.loads(x[0])
            for x in db.execute("SELECT body FROM records ORDER BY seq")
        ]
        settled = {
            x[0]: json.loads(x[1])
            for x in db.execute("SELECT id,body FROM settlements")
        }
    from . import runs

    previous = None
    for e in entries:
        if e.get("previous_commitment") != previous or e.get(
            "commitment"
        ) != runs.digest({k: v for k, v in e.items() if k != "commitment"}):
            raise ValueError("experiment commitment chain integrity failed")
        previous = e["commitment"]
    sources = {}
    for e in entries:
        if e["id"] in settled:
            sources.setdefault(e["source"], []).append({**e, **settled[e["id"]]})
    # Cross-model comparisons require matching event definitions and settlements.
    matched = {}
    for e in entries:
        if e["id"] in settled:
            matched.setdefault(e["experiment_key"], []).append(e)
    cross = []
    for key, group in matched.items():
        quant = next((e for e in group if e["source"] == "quant"), None)
        if quant:
            for e in group:
                if e["id"] == quant["id"]:
                    continue
                if (
                    runs.digest(e["event_contract"])
                    == runs.digest(quant["event_contract"])
                    and settled[e["id"]]["outcome"] == settled[quant["id"]]["outcome"]
                ):
                    cross.append(
                        {
                            "id": key,
                            "source": e["source"],
                            "as_of": e["as_of"],
                            "probabilities": e["probabilities"],
                            "reference": quant["probabilities"],
                            "outcome": settled[e["id"]]["outcome"],
                        }
                    )
    return {
        "schema": "tradefloor-scoreboard-v1",
        "registered": len(entries),
        "settled": len(settled),
        "abstained": sum(e["status"] == "abstained" for e in entries),
        "failed": sum(e["status"] == "failed" for e in entries),
        "by_source": {key: evaluation.compare(rows) for key, rows in sources.items()},
        "against_quant_on_matched_events": {
            source: evaluation.compare([r for r in cross if r["source"] == source])
            for source in {r["source"] for r in cross}
        },
        "experiments": [{**e, "settlement": settled.get(e["id"])} for e in entries],
        "integrity": "Local registry is not proof of pre-event publication. Publish externally timestamped commitments; never omit failures.",
    }
