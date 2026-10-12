"""Bounded interchange validation. Integrity is not authorship or factual verification."""

from __future__ import annotations

import math
import re
from . import events, validation as v

KINDS = {
    "scenario",
    "direction",
    "swarm",
    "analyze",
    "scout",
    "swarm-desk",
    "desk-report",
    "market-sandbox",
}


def bounded(value, depth=0, budget=None):
    budget = [250000] if budget is None else budget
    budget[0] -= 1
    if depth > 24 or budget[0] < 0:
        raise ValueError("JSON structure exceeds depth/item limits")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ValueError("JSON numbers must be finite")
    elif isinstance(value, str):
        if len(value) > 2_000_000:
            raise ValueError("JSON string exceeds limit")
    elif isinstance(value, (dict, list)):
        if isinstance(value, dict) and any(
            not isinstance(k, str) or len(k) > 200 for k in value
        ):
            raise ValueError("JSON keys must be bounded strings")
        for child in value.values() if isinstance(value, dict) else value:
            bounded(child, depth + 1, budget)
    else:
        raise ValueError("JSON contains unsupported value")


def obj(value, keys=()):
    if not isinstance(value, dict) or any(k not in value for k in keys):
        raise ValueError(f"object requires {', '.join(keys)}")
    return value


def array(value, limit=20000, minimum=0):
    if not isinstance(value, list) or not minimum <= len(value) <= limit:
        raise ValueError(f"array requires {minimum}..{limit} entries")
    return value


def quantiles(value):
    obj(value, ("p10", "p50", "p90"))
    q = [v.number(value[k], k) for k in ("p10", "p50", "p90")]
    if q != sorted(q):
        raise ValueError("quantiles must be ordered")


def simulation(value, horizon):
    obj(value, ("p_up", "p_down", "p_flat", "return_pct", "price", "fan"))
    v.probabilities({k: value["p_" + k] for k in ("up", "down", "flat")})
    quantiles(value["return_pct"])
    quantiles(value["price"])
    previous = 0
    for row in array(value["fan"], 252, 1):
        quantiles(row)
        previous = v.integer(row.get("day"), "fan.day", previous + 1, horizon)
    if previous != horizon:
        raise ValueError("fan must end at event horizon")


def bundle(payload):
    from . import snapshots

    bounded(payload)
    b = obj(
        payload,
        (
            "schema",
            "id",
            "kind",
            "request",
            "inputs",
            "result",
            "runtime",
            "parent",
            "created_at",
            "sha256",
        ),
    )
    if b["kind"] not in KINDS:
        raise ValueError("unsupported run kind")
    if not re.fullmatch(r"[a-f0-9]{64}", str(b["sha256"])):
        raise ValueError("invalid hash")
    if b["parent"] is not None and (
        not re.fullmatch(r"[a-f0-9]{32}", str(b["parent"])) or b["parent"] == b["id"]
    ):
        raise ValueError("invalid parent")
    v.timestamp(b["created_at"])
    obj(b["runtime"], ("python", "packages", "source_sha256"))
    if not re.fullmatch(r"[a-f0-9]{64}", str(b["runtime"]["source_sha256"])):
        raise ValueError("invalid runtime source hash")
    req, inputs, result = (obj(b[k]) for k in ("request", "inputs", "result"))
    kind = b["kind"]
    if kind in ("scenario", "swarm", "direction"):
        df = snapshots.restore(inputs.get("prices"))
        event = events.validate(result.get("event_contract"))
        if event["as_of"] != str(df.index[-1].date()) or not math.isclose(
            event["reference_price"], float(df.Close.iloc[-1]), rel_tol=1e-9
        ):
            raise ValueError("event does not match frozen prices")
        horizon = event["horizon_days"]
        if kind == "direction":
            v.probabilities(result.get("probabilities"))
            v.probabilities(result.get("base_rates"))
            v.direction(result.get("direction"))
            if result.get("horizon_trading_days") != horizon:
                raise ValueError("direction horizon mismatch")
            if inputs.get("benchmark") is not None:
                snapshots.restore(inputs["benchmark"])
        else:
            simulation(result.get("baseline"), horizon)
            if kind == "scenario" or "scenario" in result:
                simulation(result.get("scenario"), horizon)
                obj(result.get("shift"), ("p_up", "p_down", "median_return_pct"))
                for cls in ("up", "down"):
                    if (
                        abs(
                            result["shift"]["p_" + cls]
                            - (
                                result["scenario"]["p_" + cls]
                                - result["baseline"]["p_" + cls]
                            )
                        )
                        > 0.002
                    ):
                        raise ValueError("probability shift mismatch")
            if result.get("worlds") != req.get("worlds"):
                raise ValueError("world count mismatch")
            v.integer(req.get("seed"), "seed", 0, 2**32 - 1)
            v.integer(req.get("worlds"), "worlds", 100, 3000)
        if kind == "scenario":
            from .evidence import graph

            if req.get("case") not in ("earnings", "policy", "liquidity"):
                raise ValueError("unsupported case")
            for name, lo, hi in (
                ("sentiment", -1, 1),
                ("persistence", 0.5, 60),
                ("retail_weight", 0, 1),
            ):
                v.number(req.get(name), name, lo, hi)
            if not isinstance(req.get("sensitivity"), bool):
                raise ValueError("sensitivity must be boolean")
            g = obj(result.get("evidence_graph"), ("nodes", "edges", "cutoff"))
            nodes = array(g["nodes"], 200, 1)
            checked_graph = graph(
                [n for n in nodes if n.get("kind") != "interpretation"],
                [n for n in nodes if n.get("kind") == "interpretation"],
                g["cutoff"],
            )
            shown = {n["id"]: n for n in nodes}
            if any(
                shown[n["id"]].get("status", "active") != n["status"]
                for n in checked_graph["nodes"]
            ):
                raise ValueError("claim status does not reflect evidence dependencies")
            if (
                g.get("schema") == "tradefloor-evidence-v2"
                and g["edges"] != checked_graph["edges"]
            ):
                raise ValueError("graph edges do not reflect evidence dependencies")
            if "claims" in inputs:
                frozen_graph = graph(inputs["evidence"], inputs["claims"], g["cutoff"])
                if frozen_graph != checked_graph:
                    raise ValueError("rendered graph differs from frozen claims")
            graph(array(inputs.get("evidence"), 100, 1), [], g["cutoff"])
            by_id = {n["id"]: n for n in nodes}
            if any(
                any(
                    by_id.get(item["id"], {}).get(k) != value
                    for k, value in item.items()
                )
                for item in inputs["evidence"]
            ):
                raise ValueError("rendered evidence differs from frozen input")
            v.probabilities(obj(result.get("quant"))["probabilities"])
            simple = obj(
                result.get("simple_baseline"), ("p_up", "p_down", "return_pct")
            )
            v.probabilities(
                {
                    "up": simple["p_up"],
                    "down": simple["p_down"],
                    "flat": max(0.0, 1 - simple["p_up"] - simple["p_down"]),
                }
            )
            quantiles(simple["return_pct"])
            sweep = obj(result.get("sensitivity"), ("variants", "p_up_range"))
            for row in array(sweep["variants"], 100):
                obj(row, ("name", "p_up", "median_return_pct"))
                v.number(row["p_up"], "p_up", 0, 1)
            span = array(sweep["p_up_range"], 2, 2)
            if not 0 <= span[0] <= span[1] <= 1:
                raise ValueError("invalid sensitivity range")
            from .lab import falsification

            falsification(array(obj(result.get("falsification"))["checks"], 100, 1))
            for key in ("name", "symbol", "data_kind", "as_of"):
                if not isinstance(result.get(key), str):
                    raise ValueError(f"scenario requires {key}")
            settlement = result.get("demo_settlement")
            if settlement is not None:
                obj(settlement, ("outcome", "close", "scores", "falsification"))
                v.direction(settlement["outcome"])
                v.number(settlement["close"], "close", 1e-12)
                obj(settlement["scores"], ("brier_multiclass",))
                obj(settlement["falsification"], ("status", "checks"))
                if inputs.get("synthetic_outcome") != settlement["close"]:
                    raise ValueError("synthetic settlement differs from frozen outcome")
                expected = events.label(
                    math.log(settlement["close"] / event["reference_price"]),
                    event["flat_band"],
                )
                if settlement["outcome"] != expected:
                    raise ValueError("synthetic outcome label mismatch")
                scores = events.score(
                    {k: result["scenario"]["p_" + k] for k in ("up", "down", "flat")},
                    expected,
                )
                for key in ("brier_multiclass", "log_loss"):
                    if not math.isclose(
                        settlement["scores"].get(key, -1),
                        scores[key],
                        rel_tol=1e-8,
                        abs_tol=1e-8,
                    ):
                        raise ValueError("synthetic settlement score mismatch")
    elif kind == "market-sandbox":
        obj(
            result,
            ("tape", "trades", "participants", "conservation", "steps", "last_price"),
        )
        v.integer(req.get("steps"), "steps", 1, 500)
        array(result["tape"], 500, 1)
        array(result["trades"], 100000)
        c = obj(
            result["conservation"],
            ("cash", "inventory", "initial_cash", "initial_inventory"),
        )
        for name in ("cash", "inventory"):
            if not math.isclose(
                v.number(c[name], name, 0),
                v.number(c["initial_" + name], name, 0),
                rel_tol=1e-8,
                abs_tol=1e-6,
            ):
                raise ValueError("sandbox conservation mismatch")
        for p in obj(result["participants"]).values():
            for name in ("cash", "inventory", "reserved_cash", "reserved_inventory"):
                v.number(p.get(name), name, -1e-8)
    else:
        obj(inputs, ("settings", "prompt_sources"))
        if kind == "desk-report":
            import hashlib

            reports = obj(inputs.get("reports"))
            if not 1 <= len(reports) <= 100:
                raise ValueError("reports must contain 1..100 files")
            for name, report in reports.items():
                if "/" in name or "\\" in name:
                    raise ValueError("report name must not be a path")
                obj(report, ("content", "sha256"))
                if (
                    hashlib.sha256(report["content"].encode()).hexdigest()
                    != report["sha256"]
                ):
                    raise ValueError("report hash mismatch")
    return b
