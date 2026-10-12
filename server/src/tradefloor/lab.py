"""Offline financial scenario laboratory: frozen inputs, forks, fragility and falsification.

Examples are entirely synthetic and redistribute no third-party market data. Persona
reactions are visible user assumptions, not inferred institutional activity.
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd

from . import events, forecast, runs, snapshots, swarm, validation

CASES = {
    "earnings": {
        "name": "An earnings surprise",
        "seed": 41,
        "sentiment": 0.6,
        "persistence": 5,
        "headline": "Fictional company reports stronger earnings; management raises its outlook.",
        "alternative": "The surprise was already priced in; attention fades.",
        "actual_shock": -0.035,
    },
    "policy": {
        "name": "A policy surprise",
        "seed": 17,
        "sentiment": -0.5,
        "persistence": 12,
        "headline": "Fictional central bank tightens policy unexpectedly.",
        "alternative": "A stronger currency offsets the rate shock for importers.",
        "actual_shock": 0.025,
    },
    "liquidity": {
        "name": "A crowded exit",
        "seed": 73,
        "sentiment": -0.75,
        "persistence": 3,
        "headline": "Fictional leveraged investors need to reduce positions into thin liquidity.",
        "alternative": "Other investors absorb the selling; liquidity recovers.",
        "actual_shock": -0.09,
    },
}


def example(case: str = "earnings") -> tuple[pd.DataFrame, dict, float]:
    if case not in CASES:
        raise ValueError(f"case must be one of {', '.join(CASES)}")
    c = CASES[case]
    rng = np.random.default_rng(c["seed"])
    lr = rng.standard_t(6, 900) / math.sqrt(6 / 4) * 0.012 + 0.00015
    close = 100 * np.exp(np.cumsum(lr))
    open_ = close * np.exp(rng.normal(0, 0.003, len(close)))
    index = pd.bdate_range(end="2026-09-28", periods=len(close))
    df = pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close) * 1.005,
            "Low": np.minimum(open_, close) * 0.995,
            "Close": close,
            "Volume": rng.integers(100000, 1000000, len(close)),
        },
        index=index,
    )
    realized = float(
        close[-1] * math.exp(float(rng.normal(0, 0.012, 21).sum()) + c["actual_shock"])
    )
    return df, c, realized


def evidence_graph(evidence: list[dict], claims: list[dict], cutoff: str) -> dict:
    from .evidence import graph
    return graph(evidence, claims, cutoff)


def falsification(conditions: list[dict], observations: dict | None = None) -> dict:
    observations = observations or {}
    checks = []
    for c in conditions:
        if (
            not c.get("id")
            or not c.get("metric")
            or c.get("operator") not in ("below", "above")
            or not c.get("reason")
        ):
            raise ValueError(
                "falsification conditions require id, metric, above/below, threshold and reason"
            )
        threshold = validation.number(c["threshold"], "threshold")
        value = observations.get(c["metric"])
        value = None if value is None else validation.number(value, "observation")
        failed = (
            None
            if value is None
            else (value < threshold if c["operator"] == "below" else value > threshold)
        )
        checks.append({**c, "observed": value, "invalidated": failed})
    return {
        "checks": checks,
        "status": "invalidated"
        if any(c["invalidated"] is True for c in checks)
        else "pending observations"
        if any(c["invalidated"] is None for c in checks)
        else "survived supplied checks",
        "next_observations": [c["metric"] for c in checks if c["observed"] is None],
    }


def simulate(
    case: str = "earnings",
    sentiment: float | None = None,
    persistence: float | None = None,
    retail_weight: float = 0.2,
    seed: int = 7,
    worlds: int = 300,
    sensitivity: bool = True,
    parent_run_id: str | None = None,
    price_snapshot: dict | None = None,
    evidence: list[dict] | None = None,
    synthetic_outcome: float | None = None,
    claims: list[dict] | None = None,
    _persist: bool = True,
) -> dict:
    df, info, realized = example(case)
    synthetic = price_snapshot is None or synthetic_outcome is not None
    if synthetic_outcome is not None:
        realized = validation.number(synthetic_outcome, "synthetic_outcome", 1e-12)
    if price_snapshot is not None:
        df = snapshots.restore(price_snapshot)
    sentiment = validation.number(
        info["sentiment"] if sentiment is None else sentiment, "sentiment", -1, 1
    )
    persistence = validation.number(
        info["persistence"] if persistence is None else persistence,
        "persistence",
        0.5,
        60,
    )
    retail_weight = validation.number(retail_weight, "retail_weight", 0, 1)
    worlds = validation.integer(worlds, "worlds", 100, 1000)
    seed = validation.integer(seed, "seed", 0, 2**32 - 1)
    cut = str(df.index[-1].date()) + "T23:59:59+00:00"
    evidence = (
        evidence
        if evidence is not None
        else [
            {
                "id": "E1",
                "kind": "assumption",
                "text": info["headline"],
                "source": "fictional demo event",
            },
            {
                "id": "E2",
                "kind": "measurement",
                "text": "Frozen synthetic OHLCV history"
                if synthetic
                else "User-supplied frozen OHLCV history",
                "published_at": cut,
                "available_at": cut,
                "source": "generated fixture" if synthetic else "user snapshot",
            },
        ]
    )
    if not evidence:
        raise ValueError("at least one evidence node is required")
    claims = claims if claims is not None else [
        {
            "id": "H1",
            "text": "Participant reactions produce a persistent price shift",
            "evidence_ids": [evidence[0]["id"]],
        },
        {"id": "H2", "text": info["alternative"], "evidence_ids": [evidence[0]["id"]]},
    ]
    graph = evidence_graph(evidence, claims, cut)
    reactions = [
        {
            "group": "retail",
            "sentiment": sentiment,
            "conviction": 0.7,
            "persistence_days": persistence,
        },
        {
            "group": "hf",
            "sentiment": sentiment * 0.6,
            "conviction": 0.5,
            "persistence_days": persistence,
        },
    ]
    # Preserve remaining relative shares when changing the retail fraction.
    weights = {
        g.id: (
            retail_weight if g.id == "retail" else g.weight * (1 - retail_weight) / 0.8
        )
        for g in swarm.roster("US")
    }
    result = swarm.run(
        df, "US", 21, reactions, runs=worlds, agents=200, seed=seed, weights=weights
    )
    quant = forecast.forecast(df, 21)
    variants = []
    if sensitivity:
        for factor in (0.5, 1.5):
            rr = [
                {**r, "sentiment": max(-1, min(1, r["sentiment"] * factor))}
                for r in reactions
            ]
            v = swarm.run(
                df, "US", 21, rr, runs=worlds, agents=200, seed=seed, weights=weights
            )
            variants.append(
                {
                    "name": f"Reaction strength {factor}x",
                    "p_up": v["scenario"]["p_up"],
                    "median_return_pct": v["scenario"]["return_pct"]["p50"],
                }
            )
        for days in (1.0, 20.0):
            rr = [{**r, "persistence_days": days} for r in reactions]
            v = swarm.run(
                df, "US", 21, rr, runs=worlds, agents=200, seed=seed, weights=weights
            )
            variants.append(
                {
                    "name": f"Persistence {days:g} days",
                    "p_up": v["scenario"]["p_up"],
                    "median_return_pct": v["scenario"]["return_pct"]["p50"],
                }
            )
    p_values = [result["scenario"]["p_up"]] + [v["p_up"] for v in variants]
    conditions = [
        {
            "id": "F1",
            "metric": "horizon_close",
            "operator": "below" if sentiment >= 0 else "above",
            "threshold": float(df["Close"].iloc[-1]),
            "reason": "The directional thesis fails if the horizon close moves against it.",
        }
    ]
    result.update(
        {
            "case": case,
            "name": info["name"],
            "symbol": "SYNTHETIC" if synthetic else validation.symbol(price_snapshot.get("symbol", "USER-SNAPSHOT")),
            "as_of": str(df.index[-1].date()),
            "data_kind": "synthetic educational fixture"
            if synthetic
            else "user supplied, availability not independently verified",
            "quant": quant,
            "evidence_graph": graph,
            "falsification": falsification(conditions),
            "sensitivity": {
                "variants": variants,
                "p_up_range": [min(p_values), max(p_values)],
                "note": "Assumption sweep; this is not a confidence interval or a validated causal model.",
            },
            "simple_baseline": _simple_baseline(df, worlds, seed),
            "disclaimer": "Conditional research simulation. No orders. No demonstrated trading edge.",
        }
    )
    if synthetic:
        p = result["scenario"]
        event = result["event_contract"]
        outcome = events.label(
            math.log(realized / event["reference_price"]), event["flat_band"]
        )
        result["demo_settlement"] = {
            "outcome": outcome,
            "close": realized,
            "scores": events.score(
                {"up": p["p_up"], "down": p["p_down"], "flat": p["p_flat"]}, outcome
            ),
            "falsification": falsification(conditions, {"horizon_close": realized}),
            "note": "Held-out synthetic outcome; demonstrates settlement, not forecasting skill.",
        }
    request = {
        "case": case,
        "sentiment": sentiment,
        "persistence": persistence,
        "retail_weight": retail_weight,
        "seed": seed,
        "worlds": worlds,
        "sensitivity": sensitivity,
    }
    frozen = snapshots.frame(df)
    if not synthetic and price_snapshot:
        from .evidence import text
        for key in ("symbol", "adjustment_basis", "rights"):
            if key in price_snapshot:
                frozen[key] = text(price_snapshot[key], key, 1000)
    if synthetic:
        frozen.update(
            adjustment_basis="synthetic prices; no corporate actions",
            rights="synthetic fixture generated by MIT project code",
        )
    if not _persist:
        return result
    result["run"] = runs.create(
        "scenario",
        request,
        {
            "prices": frozen,
            "evidence": evidence,
            "claims": claims,
            "data_kind": result["data_kind"],
            "synthetic_outcome": realized if synthetic else None,
        },
        result,
        parent_run_id,
    )
    return result


def _simple_baseline(df, worlds, seed):
    profile = swarm.stock_profile(df, 21)
    rng = np.random.default_rng(seed)
    final = profile["mu_daily"] * 21 + profile["sigma_d"] * swarm._t_noise(
        rng, (worlds, 21), profile["df_t"]
    ).sum(axis=1)
    return {
        "model": "Student-t independent-return baseline, no personas",
        "p_up": float((final > profile["flat_band"]).mean()),
        "p_down": float((final < -profile["flat_band"]).mean()),
        "return_pct": {
            "p10": float(np.expm1(np.quantile(final, 0.1)) * 100),
            "p50": float(np.expm1(np.quantile(final, 0.5)) * 100),
            "p90": float(np.expm1(np.quantile(final, 0.9)) * 100),
        },
    }


def fork(run_id: str, overrides: dict) -> dict:
    original = runs.read(run_id)
    if original["kind"] != "scenario":
        raise ValueError("only scenario bundles can be forked with this tool")
    allowed = {
        "sentiment",
        "persistence",
        "retail_weight",
        "seed",
        "worlds",
        "sensitivity",
    }
    if set(overrides) - allowed:
        raise ValueError("unsupported scenario override")
    args = {
        **original["request"],
        **overrides,
        "parent_run_id": run_id,
        "evidence": original["inputs"]["evidence"],
        "claims": original["inputs"].get("claims"),
    }
    args["price_snapshot"] = original["inputs"]["prices"]
    args["synthetic_outcome"] = original["inputs"].get("synthetic_outcome")
    return simulate(**args)


def fork_evidence(run_id: str, evidence_id: str) -> dict:
    """Retract one input in a child receipt; preserve prices and numerical assumptions."""
    original = runs.read(run_id)
    if original["kind"] != "scenario":
        raise ValueError("Evidence branches require a frozen scenario")
    if not isinstance(evidence_id, str) or not any(n["id"] == evidence_id for n in original["inputs"]["evidence"]):
        raise ValueError("Select a known evidence input, not a claim")
    evidence = [{**n, "status": "retracted"} if n["id"] == evidence_id else dict(n) for n in original["inputs"]["evidence"]]
    if evidence == original["inputs"]["evidence"]:
        raise ValueError("Evidence is already retracted in this receipt")
    return simulate(**{
        **original["request"], "parent_run_id": run_id,
        "price_snapshot": original["inputs"]["prices"],
        "synthetic_outcome": original["inputs"].get("synthetic_outcome"),
        "evidence": evidence, "claims": original["inputs"].get("claims"),
    })
