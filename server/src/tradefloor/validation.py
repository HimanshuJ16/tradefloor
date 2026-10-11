"""Shared numerical invariants. Untrusted model output fails before it becomes a decision."""

from __future__ import annotations

import math
import re
from datetime import date, datetime


def number(value, name: str, low=None, high=None) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        v = float(value)
    except (TypeError, ValueError, OverflowError) as e:
        raise ValueError(f"{name} must be a finite number") from e
    if (
        not math.isfinite(v)
        or (low is not None and v < low)
        or (high is not None and v > high)
    ):
        raise ValueError(f"{name} must be finite and between {low} and {high}")
    return v


def integer(value, name: str, low=1, high=3650) -> int:
    v = number(value, name, low, high)
    if not v.is_integer():
        raise ValueError(f"{name} must be an integer")
    return int(v)


def probabilities(p: dict, name="probabilities") -> dict[str, float]:
    if not isinstance(p, dict) or set(p) != {"up", "down", "flat"}:
        raise ValueError(f"{name} requires exactly up, down and flat")
    out = {k: number(v, f"{name}.{k}", 0, 1) for k, v in p.items()}
    if abs(sum(out.values()) - 1) > 0.002:
        raise ValueError(f"{name} must sum to 1 (within rounding tolerance 0.002)")
    total = sum(out.values())
    return {k: v / total for k, v in out.items()}


def direction(value, allowed=("UP", "DOWN", "SIDEWAYS")) -> str:
    v = str(value).upper()
    if v not in allowed:
        raise ValueError(f"direction must be one of {', '.join(allowed)}")
    return v


def iso_date(value, name="date") -> str:
    try:
        return date.fromisoformat(str(value)).isoformat()
    except ValueError as e:
        raise ValueError(f"{name} must be YYYY-MM-DD") from e


def symbol(value) -> str:
    v = str(value).strip().upper()
    if not re.fullmatch(r"\^?[A-Z0-9.\-=&]{1,32}", v):
        raise ValueError("symbol must be a ticker, not a path or instruction")
    return v


def timestamp(value, name="timestamp") -> str:
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            raise ValueError("timezone required")
        return ts.isoformat()
    except ValueError as e:
        raise ValueError(f"{name} must be an ISO timestamp with timezone") from e


def decision(
    prior: dict, adjusted: dict, evidence: list[dict], adjustments: list[dict]
) -> dict:
    """Enforce the probability budget and trace each changed class to specific evidence."""
    a, b = probabilities(prior, "prior"), probabilities(adjusted, "adjusted")
    if (
        not isinstance(evidence, list)
        or not isinstance(adjustments, list)
        or len(evidence) > 100
        or len(adjustments) > 3
    ):
        raise ValueError("decision evidence/adjustments must be bounded arrays")
    if any(not isinstance(e, dict) or not e.get("text") for e in evidence):
        raise ValueError("evidence requires an object with nonempty text")
    ids = {str(e.get("id")) for e in evidence if e.get("id")}
    if len(ids) != len(evidence):
        raise ValueError("evidence requires unique nonempty IDs")
    explained = set()
    for change in adjustments:
        cls = change.get("class")
        if cls not in a or not change.get("reason") or not change.get("evidence_ids"):
            raise ValueError("adjustments require class, reason and evidence_ids")
        if not set(change["evidence_ids"]) <= ids:
            raise ValueError("adjustment cites unknown evidence")
        if cls in explained:
            raise ValueError("one aggregate adjustment per class is required")
        explained.add(cls)
        delta = number(change.get("delta"), "adjustment.delta", -0.10, 0.10)
        if abs(delta - (b[cls] - a[cls])) > 0.002:
            raise ValueError("adjustment delta does not match the probabilities")
    for cls in a:
        delta = b[cls] - a[cls]
        if abs(delta) > 0.10001 or (abs(delta) > 0.002 and cls not in explained):
            raise ValueError(
                "each probability change needs evidence and must stay within 0.10"
            )
    diff = b["up"] - b["down"]
    return {
        "valid": True,
        "probabilities": b,
        "direction": "UP" if diff >= 0.08 else "DOWN" if diff <= -0.08 else "SIDEWAYS",
    }
