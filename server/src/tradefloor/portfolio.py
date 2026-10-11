"""Exposure and covariance stress arithmetic, with explicit account units."""

from __future__ import annotations
import numpy as np
from . import validation


def stress(
    holdings: list[dict],
    shocks: dict,
    account_currency: str,
    correlation: list[list[float]] | None = None,
) -> dict:
    if not holdings or len(holdings) > 100:
        raise ValueError("portfolio requires 1..100 holdings")
    symbols, values, vols = [], [], []
    for h in holdings:
        sym = validation.symbol(h["symbol"])
        if sym in symbols:
            raise ValueError("duplicate holding; aggregate each instrument first")
        if h.get("currency") != account_currency:
            raise ValueError(
                "all holding values must already be converted to account_currency"
            )
        symbols.append(sym)
        values.append(validation.number(h["value"], "holding.value", 0))
        vols.append(validation.number(h.get("annual_vol", 0), "annual_vol", 0, 10))
    total = sum(values)
    if total <= 0:
        raise ValueError("portfolio value must be positive")
    if set(shocks) - set(symbols):
        raise ValueError("shock references unknown holding")
    changes = [
        v * validation.number(shocks.get(s, 0), f"shock.{s}", -1, 10)
        for s, v in zip(symbols, values)
    ]
    weights = np.array(values) / total
    out = {
        "account_currency": account_currency,
        "total_value": total,
        "stress_pnl": sum(changes),
        "stress_return_pct": sum(changes) / total * 100,
        "largest_position_pct": float(weights.max()) * 100,
        "concentration_hhi": float((weights**2).sum()),
        "holdings": [
            {"symbol": s, "weight": float(w), "stress_pnl": d}
            for s, w, d in zip(symbols, weights, changes)
        ],
        "assumptions": "User-supplied shocks and volatilities; deterministic exposure calculation, not a market forecast",
    }
    if correlation is not None:
        corr = np.asarray(correlation, dtype=float)
        if (
            corr.shape != (len(values), len(values))
            or not np.isfinite(corr).all()
            or not np.allclose(corr, corr.T)
            or not np.allclose(np.diag(corr), 1)
        ):
            raise ValueError(
                "correlation must be finite, symmetric and have unit diagonal"
            )
        if (np.abs(corr) > 1 + 1e-9).any() or np.linalg.eigvalsh(corr).min() < -1e-8:
            raise ValueError("correlation must be bounded and positive semidefinite")
        exposure = weights * np.array(vols)
        out["annual_vol"] = float(np.sqrt(max(0, exposure @ corr @ exposure)))
    return out
