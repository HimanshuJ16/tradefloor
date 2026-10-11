"""Explicit factor shocks, constrained allocation and option-implied scenario arithmetic."""

from __future__ import annotations
import math
import numpy as np
from . import validation as v


def factor_stress(holdings, shocks, account_currency):
    if (
        not isinstance(shocks, dict)
        or not 1 <= len(shocks) <= 30
        or not 1 <= len(holdings) <= 100
    ):
        raise ValueError("require 1..30 factors and 1..100 holdings")
    shocks = {k: v.number(value, k, -10, 10) for k, value in shocks.items()}
    rows = []
    for h in holdings:
        if h.get("currency") != account_currency:
            raise ValueError("convert holdings to account currency first")
        value = v.number(h.get("value"), "value", 0)
        loads = h.get("loadings")
        if not isinstance(loads, dict) or set(loads) != set(shocks):
            raise ValueError(
                "each holding needs explicit loadings for every factor, including zero exposures"
            )
        by_factor = {
            k: value * v.number(loads[k], "loading", -100, 100) * shock
            for k, shock in shocks.items()
        }
        rows.append(
            {
                "symbol": v.symbol(h["symbol"]),
                "value": value,
                "stress_pnl": sum(by_factor.values()),
                "factors": by_factor,
            }
        )
    if (
        len({r["symbol"] for r in rows}) != len(rows)
        or sum(r["value"] for r in rows) <= 0
    ):
        raise ValueError("positive portfolio with unique symbols required")
    return {
        "holdings": rows,
        "account_currency": account_currency,
        "stress_pnl": sum(r["stress_pnl"] for r in rows),
        "factor_pnl": {k: sum(r["factors"][k] for r in rows) for k in shocks},
        "note": "Linear user-supplied exposures and common factor shocks; residual risk and nonlinear repricing excluded.",
    }


def allocate(covariance, max_weight=0.5, iterations=2000):
    """Projected gradient for long-only fully invested minimum variance, capped weights."""
    cov = np.asarray(covariance, dtype=float)
    if (
        cov.ndim != 2
        or cov.shape[0] != cov.shape[1]
        or not 2 <= len(cov) <= 100
        or not np.isfinite(cov).all()
        or not np.allclose(cov, cov.T)
    ):
        raise ValueError("finite symmetric covariance for 2..100 assets required")
    eigen = np.linalg.eigvalsh(cov)
    if eigen.min() < -1e-10:
        raise ValueError("covariance must be positive semidefinite")
    cap = v.number(max_weight, "max_weight", 1 / len(cov), 1)
    iterations = v.integer(iterations, "iterations", 10, 10000)

    def project(x):
        lo, hi = float(x.min() - cap), float(x.max())
        for _ in range(70):
            mid = (lo + hi) / 2
            if np.clip(x - mid, 0, cap).sum() > 1:
                lo = mid
            else:
                hi = mid
        return np.clip(x - (lo + hi) / 2, 0, cap)

    w = np.ones(len(cov)) / len(cov)
    step = 1 / max(2 * eigen.max(), 1e-12)
    residual = None
    for i in range(iterations):
        nxt = project(w - step * 2 * cov @ w)
        residual = float(np.max(np.abs(nxt - w)))
        w = nxt
        if residual < 1e-10:
            break
    return {
        "weights": w.tolist(),
        "variance": max(0, float(w @ cov @ w)),
        "iterations": i + 1,
        "residual": residual,
        "converged": residual < 1e-10,
        "constraints": {"long_only": True, "sum": float(w.sum()), "max_weight": cap},
        "note": "Minimum variance under supplied covariance; estimation uncertainty, expected returns, turnover and trading costs excluded.",
    }


def option_implied(
    spot, volatility, years, rate=0, dividend_yield=0, flat_band=0.02, quote_as_of=None
):
    """Lognormal risk-neutral benchmark, explicitly separate from physical predictions."""
    spot = v.number(spot, "spot", 1e-12)
    sigma = v.number(volatility, "volatility", 1e-6, 10)
    years = v.number(years, "years", 1e-6, 30)
    rate = v.number(rate, "rate", -1, 2)
    q = v.number(dividend_yield, "dividend_yield", -1, 2)
    band = v.number(flat_band, "flat_band", 0, 5)
    v.timestamp(quote_as_of, "quote_as_of")
    norm = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
    sd = sigma * math.sqrt(years)
    mu = (rate - q - 0.5 * sigma * sigma) * years
    down = norm((-band - mu) / sd)
    up = 1 - norm((band - mu) / sd)
    d1 = (rate - q + 0.5 * sigma * sigma) * years / sd
    d2 = d1 - sd
    call = spot * (math.exp(-q * years) * norm(d1) - math.exp(-rate * years) * norm(d2))
    return {
        "measure": "risk-neutral",
        "model": "constant-volatility lognormal benchmark",
        "probabilities": {"up": up, "down": down, "flat": 1 - up - down},
        "atm_european_call": call,
        "quote_as_of": quote_as_of,
        "flat_log_return_band": band,
        "note": "Supplied volatility, not a fitted options surface. No smile, spreads or American exercise. These are not physical probabilities or trading recommendations.",
    }


def microstructure_diagnostics(tape, measured=None):
    if not isinstance(tape, list) or not 2 <= len(tape) <= 10000:
        raise ValueError("tape requires 2..10000 observations")

    def metrics(rows):
        prices = np.array([v.number(r["last"], "last", 1e-12) for r in rows])
        spreads = []
        for r in rows:
            if r.get("bid") is not None and r.get("ask") is not None:
                bid, ask = v.number(r["bid"], "bid", 0), v.number(r["ask"], "ask", 0)
                if ask < bid:
                    raise ValueError("crossed quote")
                spreads.append(ask - bid)
        return {
            "observations": len(rows),
            "return_volatility": float(np.std(np.diff(np.log(prices)))),
            "mean_spread": float(np.mean(spreads)) if spreads else None,
            "quoted_observations": len(spreads),
        }

    out = {
        "simulation": metrics(tape),
        "measured": None,
        "note": "Descriptive tape diagnostics; not calibration or proof of realistic market impact.",
    }
    if measured is not None:
        if not isinstance(measured, list) or not 2 <= len(measured) <= 10000:
            raise ValueError("measured tape requires 2..10000 observations")
        out["measured"] = metrics(measured)
    return out
