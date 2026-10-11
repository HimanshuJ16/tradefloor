"""Conservative OHLC paper fills. Forecast outcomes are scored elsewhere."""

from __future__ import annotations
import pandas as pd
from . import validation


def trade(
    session: pd.DataFrame,
    direction: int,
    trigger: float,
    stop: float,
    target: float,
    complete: bool,
    cost_bps: float = 0,
    slippage_bps: float = 0,
    square_off: str | None = None,
    entry_style: str = "breakout",
) -> dict:
    trigger, stop, target = (
        validation.number(v, n, 1e-12)
        for v, n in ((trigger, "trigger"), (stop, "stop"), (target, "target"))
    )
    if (
        direction not in (-1, 1)
        or direction * (trigger - stop) <= 0
        or direction * (target - trigger) <= 0
    ):
        raise ValueError("paper stop/target geometry is invalid")
    costs = validation.number(cost_bps, "cost_bps", 0, 1000) / 10000
    slip = validation.number(slippage_bps, "slippage_bps", 0, 1000) / 10000
    if entry_style not in ("breakout", "pullback_hold"):
        raise ValueError("invalid entry_style")
    s = session
    if square_off and not session.empty:
        cutoff = pd.Timestamp(
            f"{session.index[0].date()} {square_off}", tz=session.index.tz
        )
        s = s[s.index + pd.Timedelta(minutes=5) <= cutoff]
    if s.empty:
        return {
            "status": "scored" if complete else "open",
            "triggered": False,
            "r_multiple": 0.0,
        }
    touches = s["High"] >= trigger if direction > 0 else s["Low"] <= trigger
    if entry_style == "pullback_hold":
        touches = (
            ((s["Low"] <= trigger) & (s["Close"] >= trigger))
            if direction > 0
            else ((s["High"] >= trigger) & (s["Close"] <= trigger))
        )
    if not touches.any():
        return {
            "status": "scored" if complete else "open",
            "triggered": False,
            "r_multiple": 0.0,
            "hit": None,
        }
    after = s.loc[touches.idxmax() :]
    opening = float(after["Open"].iloc[0])
    fill = max(trigger, opening) if direction > 0 else min(trigger, opening)
    if entry_style == "pullback_hold":
        fill = float(after["Close"].iloc[0])
        after = after.iloc[
            1:
        ]  # decision at the close cannot collect a prior intrabar target
    fill *= 1 + direction * slip
    if direction * (target - fill) <= 0:
        return {
            "status": "scored",
            "triggered": False,
            "r_multiple": 0.0,
            "hit": None,
            "exit": "skipped: entry gap beyond target",
        }
    risk = direction * (fill - stop)
    stop_hit = after["Low"] <= stop if direction > 0 else after["High"] >= stop
    target_hit = after["High"] >= target if direction > 0 else after["Low"] <= target
    fs = stop_hit.idxmax() if stop_hit.any() else None
    ft = target_hit.idxmax() if target_hit.any() else None
    if fs is not None and (ft is None or fs <= ft):
        gap_open = float(after.loc[fs, "Open"])
        exit_price = min(stop, gap_open) if direction > 0 else max(stop, gap_open)
        how = "stop"
    elif ft is not None:
        exit_price, how = target, "target 1"
    elif complete:
        exit_price, how = (
            float(s["Close"].iloc[-1]),
            "time stop" if square_off else "close",
        )
    else:
        return {"status": "open", "triggered": True, "entry_fill": fill}
    exit_price *= 1 - direction * slip
    gross = direction * (exit_price - fill) / risk
    fee_r = fill * costs / risk
    return {
        "status": "scored",
        "triggered": True,
        "exit": how,
        "entry_fill": fill,
        "exit_fill": exit_price,
        "gross_r_multiple": gross,
        "cost_r": fee_r,
        "r_multiple": round(gross - fee_r, 4),
        "hit": gross - fee_r > 0,
        "fill_assumptions": "adverse gap fills; stop wins ambiguous bar; user-supplied round-trip costs and per-side slippage",
    }
