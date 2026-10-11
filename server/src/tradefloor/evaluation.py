"""Paired, date-clustered evaluation. Recommendations never auto-change the live model."""

from __future__ import annotations
import math
from collections import defaultdict
import numpy as np
from . import events, validation


def compare(cases: list[dict]) -> dict:
    if not cases or len(cases) > 20000:
        raise ValueError("evaluation needs 1..20000 matured cases")
    rows, dates, reliability = [], defaultdict(list), defaultdict(list)
    for row in cases:
        day = validation.iso_date(row["as_of"], "as_of")
        p, ref = (
            validation.probabilities(row["probabilities"]),
            validation.probabilities(row["reference"]),
        )
        own, base = events.score(p, row["outcome"]), events.score(ref, row["outcome"])
        delta = own["brier_multiclass"] - base["brier_multiclass"]
        rows.append(
            {
                "id": row.get("id"),
                "as_of": day,
                "outcome": row["outcome"],
                "score": own,
                "reference_score": base,
                "paired_delta": delta,
            }
        )
        dates[day].append(delta)
        reliability[min(9, int(p["up"] * 10))].append(
            (p["up"], float(row["outcome"] == "UP"))
        )
    clusters = np.array([np.mean(v) for _, v in sorted(dates.items())])
    mean = float(clusters.mean())
    se = (
        float(clusters.std(ddof=1) / math.sqrt(len(clusters)))
        if len(clusters) > 1
        else None
    )
    interval = [mean - 1.96 * se, mean + 1.96 * se] if se is not None else None
    return {
        "cases": len(rows),
        "session_clusters": len(clusters),
        "brier_multiclass": float(
            np.mean([r["score"]["brier_multiclass"] for r in rows])
        ),
        "reference_brier": float(
            np.mean([r["reference_score"]["brier_multiclass"] for r in rows])
        ),
        "date_balanced_delta": mean,
        "delta_interval_95": interval,
        "interval_method": "normal approximation over mean paired loss per date; not an independent-stock interval",
        "reliability_up": [
            {
                "bin": k,
                "n": len(v),
                "predicted": float(np.mean([x[0] for x in v])),
                "observed": float(np.mean([x[1] for x in v])),
            }
            for k, v in sorted(reliability.items())
        ],
        "learning_gate": "candidate for a new untouched validation period"
        if len(clusters) >= 30 and interval[1] < 0
        else "insufficient evidence: retain baseline",
        "limits": "This diagnostic cannot remove selection bias, overlapping horizons, training contamination or prove profitable trading.",
        "rows": rows,
    }


def learning_gate(training: list[dict], validation_cases: list[dict]) -> dict:
    if not training or not validation_cases:
        raise ValueError("training and untouched later validation cases required")
    ends = []
    for row in training:
        start = validation.iso_date(row["as_of"])
        end = validation.iso_date(row.get("label_end"), "training.label_end")
        if end <= start:
            raise ValueError("training label_end must follow as_of")
        ends.append(end)
    if max(ends) >= min(validation.iso_date(r["as_of"]) for r in validation_cases):
        raise ValueError(
            "validation must begin strictly after every training outcome horizon"
        )
    train = compare(training)
    holdout = compare(validation_cases)
    accepted = train["learning_gate"].startswith("candidate") and holdout[
        "learning_gate"
    ].startswith("candidate")
    return {
        "training": train,
        "holdout": holdout,
        "accepted_for_review": accepted,
        "action": "manual review under a new model version"
        if accepted
        else "retain baseline",
        "automatic_model_update": False,
    }
