"""Versioned forecast events shared by calibration, simulation and settlement."""

from __future__ import annotations

import math
from .validation import integer, number, probabilities, iso_date

VERSION = "direction-log-v1"


def current_band(close, horizon: int) -> float:
    import numpy as np

    sd = np.log(close).diff().rolling(63, min_periods=40).std().iloc[-1]
    return number(0.25 * sd * np.sqrt(integer(horizon, "horizon")), "flat_band", 0, 10)


def contract(horizon: int, band: float, as_of: str, price: float) -> dict:
    return {
        "version": VERSION,
        "return_convention": "log",
        "horizon_days": integer(horizon, "horizon"),
        "flat_band": number(band, "flat_band", 0, 10),
        "as_of": iso_date(as_of),
        "reference_price": number(price, "reference_price", 1e-12),
        "price_basis": "split/dividend adjusted; settle using the same frozen adjustment basis",
        "threshold_method": "0.25 x rolling 63-session log-return std x sqrt(horizon)",
    }


def validate(event: dict) -> dict:
    if not isinstance(event, dict) or event.get("version") not in (
        VERSION,
        "legacy-simple-v1",
    ):
        raise ValueError("unsupported event contract version")
    expected = "log" if event["version"] == VERSION else "simple"
    if event.get("return_convention") != expected:
        raise ValueError("event return convention does not match version")
    integer(event.get("horizon_days"), "event.horizon_days")
    iso_date(event.get("as_of"), "event.as_of")
    number(event.get("flat_band"), "event.flat_band", 0, 10)
    number(event.get("reference_price"), "event.reference_price", 1e-12)
    return event


def for_entry(entry: dict) -> dict:
    if entry.get("event_contract"):
        event = validate(entry["event_contract"])
        if (
            event["horizon_days"] != int(entry["horizon_days"])
            or event["as_of"] != entry["as_of"]
        ):
            raise ValueError("event contract does not match entry date/horizon")
        if not math.isclose(
            float(event["reference_price"]), float(entry["price"]), rel_tol=1e-8
        ):
            raise ValueError("event reference price does not match entry price")
        return event
    return {
        "version": "legacy-simple-v1",
        "return_convention": "simple",
        "as_of": entry["as_of"],
        "horizon_days": int(entry["horizon_days"]),
        "reference_price": float(entry["price"]),
        "flat_band": number(entry.get("flat_band_pct", 0), "flat_band_pct", 0) / 100,
        "price_basis": "legacy entry; adjustment basis not frozen",
    }


def label(value: float, band: float) -> str:
    return "UP" if value > band else "DOWN" if value < -band else "SIDEWAYS"


def score(p: dict, outcome: str) -> dict:
    p = probabilities(p)
    if outcome not in ("UP", "DOWN", "SIDEWAYS"):
        raise ValueError("unknown outcome")
    cls = {"UP": "up", "DOWN": "down", "SIDEWAYS": "flat"}[outcome]
    losses = {k: (v - float(k == cls)) ** 2 for k, v in p.items()}
    return {
        "brier_up": losses["up"],
        "brier_multiclass": sum(losses.values()),
        "brier_normalization": "sum across 3 classes, range 0..2",
        "log_loss": -math.log(max(p[cls], 1e-12)),
        "log_loss_clip": 1e-12,
    }
