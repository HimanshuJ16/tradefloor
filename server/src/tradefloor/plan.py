"""Trade plan arithmetic: entry zone, ATR stop, R-multiple targets, risk-based sizing.

Sizing rule: the loss if the stop is hit equals risk_pct of capital, capped so a single
position never exceeds max_position_pct of capital. Quantity is rounded down to lot size.
"""

from __future__ import annotations

import math
from . import validation


def stop_multiple(horizon_days: int) -> float:
    """ATR multiple for the stop. Wider for longer holds; 1.5x at a week, capped at 4x."""
    return round(min(4.0, max(1.5, 1.5 * math.sqrt(horizon_days / 5))), 2)


def build_plan(
    price: float,
    atr: float,
    direction: str,
    horizon_days: int,
    capital: float = 0.0,
    risk_pct: float = 1.0,
    max_position_pct: float = 20.0,
    lot_size: int = 1,
    range_high: float | None = None,
    range_low: float | None = None,
    allow_short: bool = False,
    quote_unit_scale: float = 1.0,
    contract_multiplier: float = 1.0,
    fx_to_account: float = 1.0,
    quantity_step: float | None = None,
    cost_bps: float = 0.0,
) -> dict:
    direction = validation.direction(direction)
    price = validation.number(price, "price", 1e-12)
    atr = validation.number(atr, "atr", 1e-12)
    validation.integer(horizon_days, "horizon_days")
    capital = validation.number(capital, "capital", 0)
    risk_pct = validation.number(risk_pct, "risk_pct", .01, 5)
    max_position_pct = validation.number(max_position_pct, "max_position_pct", .01, 100)
    validation.integer(lot_size, "lot_size", 1, 10**9)
    scale = validation.number(quote_unit_scale, "quote_unit_scale", 1e-12)
    multiplier = validation.number(contract_multiplier, "contract_multiplier", 1e-12)
    fx = validation.number(fx_to_account, "fx_to_account", 1e-12)
    costs = validation.number(cost_bps, "cost_bps", 0, 1000)
    step = validation.number(quantity_step if quantity_step is not None else lot_size, "quantity_step", 1e-12)
    if direction == "SIDEWAYS":
        return {
            "side": "none",
            "action": "No directional trade. Hold existing positions; consider range tactics only if you already trade them.",
            "range_hint": {"low": range_low, "high": range_high},
        }
    long = direction == "UP"
    if not long and not allow_short:
        return {
            "side": "reduce",
            "action": "Bearish view. For holders: reduce, tighten stops, or hedge. Short only if your market and account permit it (pass allow_short=true).",
            "suggested_protective_stop_for_holders": round(price - stop_multiple(horizon_days) * atr, 4),
            "range_hint": {"low": range_low, "high": range_high},
        }

    k = stop_multiple(horizon_days)
    sgn = 1 if long else -1
    risk_per_unit = k * atr
    entry_lo, entry_hi = (price - 0.5 * atr, price) if long else (price, price + 0.5 * atr)
    stop = price - sgn * risk_per_unit
    targets = [round(price + sgn * m * risk_per_unit, 4) for m in (1.5, 2.5)]
    band_edge = range_high if long else range_low
    if band_edge is not None and (band_edge - price) * sgn > 0:
        targets.append(round(band_edge, 4))
    targets = sorted(set(targets), reverse=not long)

    plan = {
        "side": "long" if long else "short",
        "entry_zone": [round(entry_lo, 4), round(entry_hi, 4)],
        "stop": round(stop, 4),
        "stop_atr_multiple": k,
        "risk_per_unit": round(risk_per_unit, 4),
        "targets": targets,
        "reward_to_risk": [round(abs(t - price) / risk_per_unit, 2) for t in targets],
        "time_stop": f"Exit or re-evaluate after {horizon_days} trading days if neither stop nor target is hit.",
    }
    if stop <= 0:
        plan["warning"] = "Stop at or below zero: volatility is too high for this horizon. Shorten the horizon or skip."
        plan["side"] = "none"
        plan["sizing_status"] = "blocked: invalid stop geometry"
        return plan

    if capital and capital > 0:
        risk_budget = capital * risk_pct / 100
        unit_value = price * scale * multiplier * fx
        unit_risk = (risk_per_unit + price * costs / 10000) * scale * multiplier * fx
        qty = risk_budget / unit_risk
        cap_qty = capital * max_position_pct / 100 / unit_value
        capped = qty > cap_qty
        qty = min(qty, cap_qty)
        qty = round(math.floor(min(qty, cap_qty) / step) * step, 10)
        plan["sizing"] = {
            "capital": capital,
            "risk_pct": risk_pct,
            "risk_budget": round(risk_budget, 2),
            "quantity": qty,
            "lot_size": lot_size, "quantity_step": step,
            "position_value": round(qty * unit_value, 2),
            "position_pct_of_capital": round(qty * unit_value / capital * 100, 2),
            "loss_at_stop": round(qty * unit_risk, 2),
            "units": {"quote_unit_scale": scale, "contract_multiplier": multiplier, "fx_to_account": fx},
            "round_trip_cost_bps": costs,
            "capped_by_max_position_pct": capped,
        }
        if qty == 0:
            plan["sizing"]["note"] = "Quantity rounds to zero: the lot or one unit risks more than the budget."
    return plan
