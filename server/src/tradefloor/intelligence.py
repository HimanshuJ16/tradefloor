"""Accountable research memory, preregistration and bounded experiment proposals."""

from __future__ import annotations
import json
import uuid
from urllib.parse import urlsplit
from . import research, runs, validation as v
from .evidence import stamp, text
from .storage import canonical, connect


def append(kind, payload):
    from .schemas import bounded

    bounded(payload)
    if kind not in ("assessment", "outcome", "protocol", "witness", "proposal"):
        raise ValueError("unsupported research record")
    p = dict(payload)
    p.update(kind=kind, recorded_at=research.now(), id=uuid.uuid4().hex)
    if kind == "assessment":
        for key in (
            "model_id",
            "model_version",
            "prompt_version",
            "claim",
            "context",
            "phase",
        ):
            text(p.get(key), key, 4000)
        if p["phase"] not in ("independent", "revision"):
            raise ValueError("phase must be independent or revision")
        stamp(p.get("as_of"))
        if stamp(p.get("expires_at")) <= stamp(p["as_of"]):
            raise ValueError("expiry must follow assessment cutoff")
        v.probabilities(p.get("probabilities"))
        for key in ("evidence_ids", "tool_receipts"):
            if not isinstance(p.get(key), list) or len(p[key]) > 100:
                raise ValueError(f"{key} must be a bounded list")
        for key in ("latency_ms", "tokens"):
            v.number(p.get(key), key, 0)
        if p.get("cost_usd") is not None:
            v.number(p["cost_usd"], "cost_usd", 0)
    elif kind == "outcome":
        runs.identity(p.get("assessment_id"))
        v.direction(p.get("outcome"))
        stamp(p.get("available_at"))
    elif kind == "protocol":
        text(p.get("name"), "name", 160)
        text(p.get("schedule"), "schedule", 500)
        text(p.get("primary_endpoint"), "primary_endpoint", 500)
        text(p.get("settlement_rule"), "settlement_rule", 2000)
        v.integer(p.get("trial_budget"), "trial_budget", 1, 10000)
        if (
            not isinstance(p.get("universe"), list)
            or not 1 <= len(p["universe"]) <= 1000
        ):
            raise ValueError("fixed universe required")
        p["universe"] = [v.symbol(s) for s in p["universe"]]
        if len(set(p["universe"])) != len(p["universe"]):
            raise ValueError("duplicate universe members")
        if stamp(p.get("holdout_start")) <= stamp(p.get("training_label_end")):
            raise ValueError("holdout must follow all training outcome horizons")
        p["publication_status"] = "local only; not preregistered externally"
    elif kind == "witness":
        text(p.get("commitment_sha256"), "commitment_sha256", 64)
        if len(p["commitment_sha256"]) != 64 or any(
            c not in "0123456789abcdef" for c in p["commitment_sha256"]
        ):
            raise ValueError("invalid commitment hash")
        url = urlsplit(text(p.get("url"), "url", 2000))
        if url.scheme != "https" or not url.hostname:
            raise ValueError("witness requires an HTTPS publication URL")
        stamp(p.get("claimed_published_at"))
        p["verification_status"] = (
            "unverified supplied witness; no external timestamp verification performed"
        )
    else:
        for key in ("hypothesis", "test_plan", "model_family", "protocol_id"):
            text(p.get(key), key, 4000)
        if p.get("status", "proposed") not in (
            "proposed",
            "failed",
            "completed",
            "rejected",
        ):
            raise ValueError("invalid proposal status")
        p["execution"] = "data-only proposal; no arbitrary code execution"
    with connect(research.database()) as db:
        if kind == "outcome":
            row = db.execute(
                "SELECT body FROM records WHERE id=?",
                ("assessment:" + p["assessment_id"],),
            ).fetchone()
            if not row:
                raise ValueError("assessment not found")
            assessment = json.loads(row[0])
            if stamp(p["available_at"]) < stamp(assessment["expires_at"]):
                raise ValueError(
                    "outcome cannot be available before the assessment horizon"
                )
            if db.execute(
                "SELECT 1 FROM records WHERE id LIKE 'outcome:%' AND json_extract(body,'$.assessment_id')=?",
                (p["assessment_id"],),
            ).fetchone():
                raise ValueError("assessment is already settled")
        if kind == "proposal":
            row = db.execute(
                "SELECT body FROM records WHERE id=?", ("protocol:" + p["protocol_id"],)
            ).fetchone()
            if not row:
                raise ValueError("protocol not found")
            count = db.execute(
                "SELECT count(*) FROM records WHERE id LIKE 'proposal:%' AND json_extract(body,'$.protocol_id')=?",
                (p["protocol_id"],),
            ).fetchone()[0]
            if count >= json.loads(row[0])["trial_budget"]:
                raise ValueError("protocol trial budget exhausted")
        p["sha256"] = runs.digest(p)
        db.execute(
            "INSERT INTO records(id,body) VALUES (?,?)",
            (kind + ":" + p["id"], canonical(p)),
        )
    return p


def memory(cutoff, context=None):
    from . import events

    end = stamp(cutoff)
    with connect(research.database()) as db:
        records = [
            json.loads(r[0])
            for r in db.execute(
                "SELECT body FROM records WHERE id LIKE 'assessment:%' OR id LIKE 'outcome:%'"
            )
        ]
    # recorded_at matters: users cannot backdate memory into a prior replay.
    assessments = {
        r["id"]: r
        for r in records
        if r["kind"] == "assessment"
        and stamp(r["as_of"]) <= end
        and stamp(r["recorded_at"]) <= end
        and (context is None or r["context"] == context)
    }
    scored = []
    for row in records:
        if (
            row["kind"] != "outcome"
            or row["assessment_id"] not in assessments
            or stamp(row["available_at"]) > end
            or stamp(row["recorded_at"]) > end
        ):
            continue
        a = assessments[row["assessment_id"]]
        scored.append(
            {
                "assessment_id": a["id"],
                "model_id": a["model_id"],
                "model_version": a["model_version"],
                "phase": a["phase"],
                **events.score(a["probabilities"], row["outcome"]),
            }
        )
    return {
        "assessments": list(assessments.values()),
        "scores": scored,
        "note": "Only records and outcomes available by the cutoff. Descriptive scores, no automatic trust weights or model promotion.",
    }
