"""Versioned forecast interchange and a reproducible baseline arena."""

from __future__ import annotations
import math
import time
import numpy as np
from . import events, forecast, research, runs, snapshots, validation as v
from .storage import canonical, connect

MODELS = {
    "quant": "Existing price-only conditional frequencies",
    "bootstrap": "IID resampled daily log returns; dependence not modeled",
    "ewma": "Zero-drift Gaussian returns with EWMA volatility",
    "student": "Independent Student-t returns with historical mean and variance",
}


def validate_forecast(receipt, event):
    if receipt.get("schema") != "tradefloor-forecast-v1":
        raise ValueError("unsupported forecast adapter schema")
    if events.validate(receipt.get("event_contract")) != event:
        raise ValueError("forecast event contract mismatch")
    from .evidence import text

    text(receipt.get("model_id"), "model_id", 160)
    text(receipt.get("model_version"), "model_version", 160)
    v.probabilities(receipt.get("probabilities"))
    v.number(receipt.get("latency_ms"), "latency_ms", 0)
    if receipt.get("cost_usd") is not None:
        v.number(receipt["cost_usd"], "cost_usd", 0)
    if not isinstance(receipt.get("provenance"), dict) or not receipt["provenance"]:
        raise ValueError("forecast needs provenance")
    return receipt


def forecast_run(run_id, seed=7, draws=2000, external=None):
    b = runs.read(run_id)
    if b["kind"] not in ("scenario", "direction", "swarm"):
        raise ValueError("arena needs a frozen price run")
    seed = v.integer(seed, "seed", 0, 2**32 - 1)
    draws = v.integer(draws, "draws", 100, 10000)
    df = snapshots.restore(b["inputs"]["prices"])
    event = b["result"]["event_contract"]
    h, band = event["horizon_days"], event["flat_band"]
    if h * draws > 2_520_000:
        raise ValueError("arena draw budget exceeded")
    returns = np.diff(np.log(df.Close.to_numpy(dtype=float)))[-756:]
    rows = []
    for name, description in MODELS.items():
        start = time.perf_counter()
        rng = np.random.default_rng(seed)
        if name == "quant":
            p = forecast.forecast(df, h)["probabilities"]
            percentiles = None
        else:
            if name == "bootstrap":
                sample = rng.choice(returns, size=(draws, h)).sum(axis=1)
            elif name == "ewma":
                weights = 0.94 ** np.arange(len(returns) - 1, -1, -1)
                sigma = math.sqrt(float(np.average(returns**2, weights=weights)))
                sample = rng.normal(0, sigma * math.sqrt(h), size=draws)
            else:
                sample = returns.mean() * h + returns.std(ddof=1) * rng.standard_t(
                    6, (draws, h)
                ).sum(axis=1) / math.sqrt(1.5)
            p = {
                "up": float((sample > band).mean()),
                "down": float((sample < -band).mean()),
                "flat": float((abs(sample) <= band).mean()),
            }
            percentiles = dict(
                zip(
                    ("p10", "p50", "p90"),
                    np.expm1(np.quantile(sample, [0.1, 0.5, 0.9])).tolist(),
                )
            )
        rows.append(
            validate_forecast(
                {
                    "schema": "tradefloor-forecast-v1",
                    "model_id": name,
                    "model_version": "1",
                    "event_contract": event,
                    "probabilities": p,
                    "return_quantiles": percentiles,
                    "latency_ms": (time.perf_counter() - start) * 1000,
                    "cost_usd": 0,
                    "provenance": {
                        "source_run_id": run_id,
                        "source_sha256": b["sha256"],
                        "seed": seed,
                        "draws": draws,
                        "method": description,
                    },
                },
                event,
            )
        )
    if external:
        if not isinstance(external, list) or len(external) > 20:
            raise ValueError("at most 20 external forecasts")
        rows.extend(validate_forecast(r, event) for r in external)
    if len({(r["model_id"], r["model_version"]) for r in rows}) != len(rows):
        raise ValueError("duplicate model/version in arena")
    result = {
        "schema": "tradefloor-arena-v1",
        "source_run_id": run_id,
        "created_at": research.now(),
        "forecasts": rows,
        "note": "Predictions on identical frozen inputs; no ranking of skill without held-out outcomes. External model provenance is supplied, not verified.",
    }
    result["sha256"] = runs.digest(result)
    with connect(research.database()) as db:
        db.execute(
            "INSERT OR IGNORE INTO records(id,body) VALUES (?,?)",
            ("arena:" + result["sha256"], canonical(result)),
        )
    return result


def evaluate(cases, block_length=5, bootstrap_draws=1000, seed=7, trials=1):
    """Moving blocks of ordered observation dates; all class calibration and paired losses."""
    from .evaluation import compare

    base = compare(cases)
    length = v.integer(block_length, "block_length", 1, 252)
    draws = v.integer(bootstrap_draws, "bootstrap_draws", 200, 5000)
    v.integer(seed, "seed", 0, 2**32 - 1)
    trials = v.integer(trials, "trials", 1, 1000000)
    by_date = {}
    reliability = {k: {} for k in ("up", "down", "flat")}
    outcomes = {"UP": "up", "DOWN": "down", "SIDEWAYS": "flat"}
    for case, row in zip(cases, base["rows"]):
        by_date.setdefault(row["as_of"], []).append(
            [
                row["paired_delta"],
                row["score"]["log_loss"] - row["reference_score"]["log_loss"],
            ]
        )
        p = v.probabilities(case["probabilities"])
        for cls in reliability:
            reliability[cls].setdefault(min(9, int(p[cls] * 10)), []).append(
                (p[cls], float(outcomes[case["outcome"]] == cls))
            )
    matrix = np.array([np.mean(by_date[d], axis=0) for d in sorted(by_date)])
    n = len(matrix)
    interval = None
    if n >= max(2 * length, 10):
        rng = np.random.default_rng(seed)
        means = []
        for _ in range(draws):
            starts = rng.integers(0, n - length + 1, size=math.ceil(n / length))
            idx = np.concatenate([np.arange(s, s + length) for s in starts])[:n]
            means.append(matrix[idx].mean(axis=0))
        lo, hi = np.quantile(means, [0.025, 0.975], axis=0)
        interval = {
            "brier": [float(lo[0]), float(hi[0])],
            "log_loss": [float(lo[1]), float(hi[1])],
        }
    return {
        **base,
        "date_balanced_log_loss_delta": float(matrix[:, 1].mean()),
        "block_intervals_95": interval,
        "block_length_dates": length,
        "bootstrap_draws": draws,
        "seed": seed,
        "trials": trials,
        "reliability": {
            cls: [
                {
                    "bin": i,
                    "n": len(vals),
                    "predicted": float(np.mean([x[0] for x in vals])),
                    "observed": float(np.mean([x[1] for x in vals])),
                }
                for i, vals in sorted(bins.items())
            ]
            for cls, bins in reliability.items()
        },
        "learning_gate": "manual review only; this report cannot authorize model promotion",
        "inference_note": "Moving-block percentile bootstrap on ordered dates. Choose block length for dependence and inspect sensitivity. Intervals are not corrected for multiple trials; preregister and retain an untouched holdout.",
    }
