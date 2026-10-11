"""Persistent research projects, exact branch differences and bounded counterexamples."""

from __future__ import annotations

import itertools
import json
import uuid
from datetime import datetime, timezone
from . import lab, runs, settings, validation as v
from .evidence import text
from .storage import canonical, connect


def now():
    return datetime.now(timezone.utc).isoformat()


def database():
    return settings.home() / "research.sqlite3"


def project(action="list", project_id=None, body=None):
    body = body or {}
    if action == "list":
        with connect(database()) as db:
            rows = [
                json.loads(x[0])
                for x in db.execute(
                    "SELECT body FROM config WHERE key LIKE 'project:%'"
                )
            ]
        return {"projects": sorted(rows, key=lambda p: p["updated_at"], reverse=True)}
    if action == "create":
        p = {
            "id": uuid.uuid4().hex,
            "title": text(body.get("title"), "title", 160),
            "question": text(body.get("question", body.get("title")), "question", 2000),
            "revision": 1,
            "runs": [],
            "evidence": [],
            "claims": [],
            "cutoff": body.get("cutoff", now()),
            "created_at": now(),
            "updated_at": now(),
        }
        v.timestamp(p["cutoff"])
        with connect(database()) as db:
            db.execute(
                "INSERT INTO config VALUES (?,?)", ("project:" + p["id"], canonical(p))
            )
        return p
    runs.identity(project_id)
    with connect(database()) as db:
        row = db.execute(
            "SELECT body FROM config WHERE key=?", ("project:" + project_id,)
        ).fetchone()
        if row is None:
            raise ValueError("project not found")
        p = json.loads(row[0])
        if action == "get":
            return p
        if action == "history":
            return {
                "revisions": [
                    json.loads(r[0])
                    for r in db.execute(
                        "SELECT body FROM records WHERE id LIKE ? ORDER BY seq",
                        (project_id + ":%",),
                    )
                ]
                + [p]
            }
        if action not in ("update", "attach"):
            raise ValueError("unknown project action")
        if body.get("revision") != p["revision"]:
            raise ValueError("project changed; reload before saving")
        previous = canonical(p)
        if action == "attach":
            b = runs.read(body.get("run_id"))
            if b["kind"] != "scenario":
                raise ValueError("workspace accepts scenario runs")
            if b["id"] not in [r["id"] for r in p["runs"]]:
                if len(p["runs"]) >= 100:
                    raise ValueError("project limit is 100 runs")
                p["runs"].append(
                    {
                        "id": b["id"],
                        "label": text(
                            body.get("label", f"Branch {len(p['runs']) + 1}"),
                            "label",
                            160,
                        ),
                        "parent": b["parent"],
                    }
                )
        else:
            from .evidence import graph

            allowed = {"title", "question", "cutoff", "evidence", "claims", "revision"}
            if set(body) - allowed:
                raise ValueError("unsupported project field")
            p.update({k: val for k, val in body.items() if k != "revision"})
            text(p["title"], "title", 160)
            text(p["question"], "question", 2000)
            p["graph"] = graph(p["evidence"], p["claims"], p["cutoff"])
        db.execute(
            "INSERT INTO records(id,body) VALUES (?,?)",
            (project_id + ":" + str(p["revision"]), previous),
        )
        p.update(revision=p["revision"] + 1, updated_at=now())
        db.execute(
            "UPDATE config SET body=? WHERE key=?",
            (canonical(p), "project:" + project_id),
        )
        return p


def export_project(project_id, include_data=False):
    p = project("get", project_id)
    if not include_data:
        return {
            "schema": "tradefloor-project-summary-v1",
            "title": p["title"],
            "question": p["question"],
            "runs": p["runs"],
            "note": "Summary only; no evidence text, source data or importable receipts.",
        }
    # Canonical strings prevent browser parse/stringify from changing integral floats and hashes.
    pending = [r["id"] for r in p["runs"]]
    bundles = {}
    while pending:
        identifier = pending.pop()
        if identifier in bundles:
            continue
        if len(bundles) >= 200:
            raise ValueError("project ancestry exceeds export limit")
        b = runs.read(identifier)
        bundles[identifier] = canonical(b)
        if b["parent"]:
            pending.append(b["parent"])
    out = {
        "schema": "tradefloor-project-v1",
        "project": p,
        "bundles": list(bundles.values()),
        "sharing": "Contains source data and private research. Check redistribution rights before sharing.",
    }
    if len(canonical(out).encode()) > 20_000_000:
        raise ValueError("project export exceeds 20 MB")
    return out


def project_scenario(project_id, run_id):
    """Freeze edited evidence into a child; evidence text does not automatically change returns."""
    p = project("get", project_id)
    b = runs.read(run_id)
    if b["kind"] != "scenario" or not p["evidence"]:
        raise ValueError("scenario run and nonempty project evidence required")
    return lab.simulate(
        **b["request"],
        price_snapshot=b["inputs"]["prices"],
        synthetic_outcome=b["inputs"].get("synthetic_outcome"),
        evidence=p["evidence"],
        claims=p["claims"],
        parent_run_id=run_id,
    )


def import_project(payload):
    from . import schemas
    from .evidence import graph

    schemas.bounded(payload)
    if (
        payload.get("schema") != "tradefloor-project-v1"
        or len(canonical(payload).encode()) > 20_000_000
    ):
        raise ValueError("unsupported or oversized project")
    p = dict(payload["project"])
    runs.identity(p["id"])
    text(p["title"], "title", 160)
    text(p["question"], "question", 2000)
    p["graph"] = graph(p["evidence"], p["claims"], p["cutoff"])
    bundles = [
        runs.verify(json.loads(b)) for b in schemas.array(payload["bundles"], 200)
    ]
    ids = {b["id"] for b in bundles}
    if len(ids) != len(bundles):
        raise ValueError("duplicate bundle IDs")
    schemas.array(p["runs"], 100)
    if len({r["id"] for r in p["runs"]}) != len(p["runs"]) or any(
        r["id"] not in ids for r in p["runs"]
    ):
        raise ValueError("project references missing or duplicated runs")
    by_id = {b["id"]: b for b in bundles}
    for b in bundles:
        seen = set()
        node = b
        while node:
            if node["id"] in seen:
                raise ValueError("bundle lineage cycle")
            seen.add(node["id"])
            parent = node["parent"]
            if parent and parent not in ids:
                raise ValueError("project omits ancestor")
            node = by_id.get(parent)
    for row in p["runs"]:
        text(row["label"], "label", 160)
        if row.get("parent") != by_id[row["id"]]["parent"]:
            raise ValueError("project lineage mismatch")
    # Verify all existing IDs before any writes.
    for b in bundles:
        if (runs.root() / b["id"] / "bundle.json").exists() and runs.read(b["id"])[
            "sha256"
        ] != b["sha256"]:
            raise ValueError("run ID conflict")
    for b in bundles:
        runs.import_bundle(b)
    p.update(id=uuid.uuid4().hex, revision=1, updated_at=now(), imported_from=p["id"])
    with connect(database()) as db:
        db.execute(
            "INSERT INTO config VALUES (?,?)", ("project:" + p["id"], canonical(p))
        )
    return p


def difference(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        result = []
        for k in sorted(set(a) | set(b)):
            result.extend(difference(a.get(k), b.get(k), f"{path}.{k}".lstrip(".")))
        return result
    return [] if a == b else [{"field": path, "before": a, "after": b}]


def compare(run_ids):
    if (
        not isinstance(run_ids, list)
        or not 2 <= len(run_ids) <= 4
        or len(set(run_ids)) != len(run_ids)
    ):
        raise ValueError("compare two to four distinct runs")
    bundles = [runs.read(i) for i in run_ids]
    base = bundles[0]
    if any(b["kind"] != "scenario" for b in bundles):
        raise ValueError("comparison requires scenario runs")
    if any(
        b["result"]["event_contract"] != base["result"]["event_contract"]
        for b in bundles
    ):
        raise ValueError("event definitions differ; paired comparison refused")
    if any(b["inputs"]["prices"] != base["inputs"]["prices"] for b in bundles):
        raise ValueError("frozen histories differ; paired comparison refused")
    return {
        "event_contract": base["result"]["event_contract"],
        "rows": [
            {
                "id": b["id"],
                "parent": b["parent"],
                "probabilities": probabilities(b["result"]),
                "return_pct": b["result"]["scenario"]["return_pct"],
                "delta_p_up": b["result"]["scenario"]["p_up"]
                - base["result"]["scenario"]["p_up"],
                "changes": difference(base["request"], b["request"], "request")
                + difference(base["inputs"], b["inputs"], "inputs")
                + difference(base["runtime"], b["runtime"], "runtime"),
                "randomness_pairing": "same seed and dimensions; conditional on model"
                if all(
                    b["request"][k] == base["request"][k] for k in ("seed", "worlds")
                )
                and b["runtime"] == base["runtime"]
                else "not established",
            }
            for b in bundles
        ],
    }


def probabilities(result):
    return v.probabilities(
        {k: result["scenario"]["p_" + k] for k in ("up", "down", "flat")}
    )


def direction(p):
    d = p["up"] - p["down"]
    return "UP" if d >= 0.08 else "DOWN" if d <= -0.08 else "SIDEWAYS"


def challenge(run_id, bounds=None, points=3, budget=40, progress=None):
    """Exhaustive distance-ordered finite grid; no claim about the continuous optimum."""
    b = runs.read(run_id)
    if b["kind"] != "scenario":
        raise ValueError("challenge requires a scenario")
    points = v.integer(points, "points", 2, 5)
    budget = v.integer(budget, "budget", 1, 150)
    domains = {"sentiment": [-1, 1], "persistence": [0.5, 60], "retail_weight": [0, 1]}
    bounds = bounds or {
        "sentiment": [-1, 1],
        "persistence": [1, 20],
        "retail_weight": [0.1, 0.5],
    }
    if not isinstance(bounds, dict) or not bounds or set(bounds) - set(domains):
        raise ValueError("bounds require sentiment, persistence and/or retail_weight")
    import numpy as np

    grid = {}
    for name, span in bounds.items():
        if not isinstance(span, list) or len(span) != 2:
            raise ValueError("bounds must have two endpoints")
        lo, hi = [v.number(x, name, *domains[name]) for x in span]
        if lo >= hi or not lo <= b["request"][name] <= hi:
            raise ValueError(
                "bounds must contain the original assumption with positive width"
            )
        grid[name] = sorted(
            set([*np.linspace(lo, hi, points).tolist(), b["request"][name]])
        )
    candidates = [
        dict(zip(grid, values)) for values in itertools.product(*grid.values())
    ]
    distance = lambda item: (
        sum(
            ((item[k] - b["request"][k]) / (bounds[k][1] - bounds[k][0])) ** 2
            for k in grid
        )
        ** 0.5
    )
    candidates.sort(key=distance)
    original = direction(probabilities(b["result"]))
    rows, found = [], None
    for item in candidates[:budget]:
        if progress:
            progress(len(rows), min(budget, len(candidates)))
        out = lab.simulate(
            **{**b["request"], **item, "sensitivity": False},
            price_snapshot=b["inputs"]["prices"],
            evidence=b["inputs"]["evidence"],
            synthetic_outcome=b["inputs"].get("synthetic_outcome"),
            _persist=False,
        )
        p = probabilities(out)
        row = {
            "assumptions": item,
            "distance": distance(item),
            "direction": direction(p),
            "probabilities": p,
        }
        rows.append(row)
        if row["direction"] != original:
            found = row
            break
    receipt = None
    if found:
        receipt = lab.fork(run_id, found["assumptions"])["run"]
    return {
        "schema": "tradefloor-challenge-v1",
        "source_run_id": run_id,
        "original_direction": original,
        "rule": "UP if P(UP)-P(DOWN)>=0.08; DOWN if <=-0.08; otherwise SIDEWAYS",
        "bounds": bounds,
        "grid_points": grid,
        "candidate_count": len(candidates),
        "evaluated": len(rows),
        "distance_metric": "Euclidean distance normalized by supplied parameter spans",
        "status": "counterexample found"
        if found
        else "no reversal found within evaluated grid",
        "counterexample": found,
        "run": receipt,
        "rows": rows,
        "boundary": bool(
            found and any(found["assumptions"][k] in bounds[k] for k in grid)
        ),
        "guarantee": "nearest reversing point in distance-ordered grid"
        if found
        else "none",
        "limits": "Finite grid, conditional model and Monte Carlo noise. Not a continuous optimum, causal proof or robustness guarantee.",
    }


def investigate(run_id):
    b = runs.read(run_id)
    if b["kind"] != "scenario":
        raise ValueError("investigation requires scenario")
    suggestions = []
    for name, span in {
        "sentiment": [-1, 1],
        "persistence": [0.5, 60],
        "retail_weight": [0, 1],
    }.items():
        vals = []
        for value in span:
            out = lab.simulate(
                **{**b["request"], name: value, "sensitivity": False},
                price_snapshot=b["inputs"]["prices"],
                evidence=b["inputs"]["evidence"],
                synthetic_outcome=b["inputs"].get("synthetic_outcome"),
                _persist=False,
            )
            vals.append(out["scenario"]["p_up"])
        suggestions.append(
            {
                "assumption": name,
                "bounds": span,
                "p_up_at_endpoints": vals,
                "sensitivity": abs(vals[1] - vals[0]),
            }
        )
    return {
        "ranking": sorted(suggestions, key=lambda x: -x["sensitivity"]),
        "method": "one-assumption-at-a-time endpoint sensitivity; interactions and probabilities of assumptions unknown",
        "not_expected_value_of_information": True,
    }
