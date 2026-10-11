"""Typed evidence, source lineage and time-restricted claim dependencies."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from difflib import SequenceMatcher
from . import validation as v


def stamp(value):
    return datetime.fromisoformat(v.timestamp(value)).astimezone(timezone.utc)


def text(value, name="text", limit=10000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be nonempty text, at most {limit} characters")
    return value


def graph(evidence: list[dict], claims: list[dict], cutoff: str) -> dict:
    if (
        not isinstance(evidence, list)
        or not isinstance(claims, list)
        or len(evidence) > 100
        or len(claims) > 100
    ):
        raise ValueError("at most 100 evidence items and 100 claims")
    end = stamp(cutoff)
    nodes, ids, content_ids, duplicates, families = [], set(), {}, [], {}
    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError("evidence must be objects")
        identifier = text(item.get("id"), "id", 100)
        if identifier in ids:
            raise ValueError("evidence IDs must be unique")
        ids.add(identifier)
        body = text(item.get("text"))
        kind = item.get("kind")
        if kind not in ("measurement", "source", "assumption"):
            raise ValueError("evidence kind must be measurement/source/assumption")
        published, available = item.get("published_at"), item.get("available_at")
        if kind != "assumption" and not (published and available):
            raise ValueError("dated evidence requires published_at and available_at")
        if any(stamp(s) > end for s in (published, available) if s):
            raise ValueError("evidence was not available at the frozen cutoff")
        if published and available and stamp(available) < stamp(published):
            raise ValueError("availability cannot precede publication")
        status = item.get("status", "active")
        if status not in ("active", "retracted", "disputed"):
            raise ValueError("unsupported evidence status")
        anchor = item.get("anchor")
        if anchor is not None:
            if not isinstance(anchor, dict) or not isinstance(
                anchor.get("document_text"), str
            ):
                raise ValueError("anchor needs document_text, start and end")
            document = text(anchor["document_text"], "document", 200000)
            start = v.integer(anchor.get("start"), "anchor.start", 0, len(document))
            stop = v.integer(anchor.get("end"), "anchor.end", start + 1, len(document))
            if document[start:stop] != body:
                raise ValueError("evidence text must exactly match its document anchor")
            actual = hashlib.sha256(document.encode()).hexdigest()
            if item.get("document_sha256", actual) != actual:
                raise ValueError("document hash mismatch")
        key = " ".join(body.lower().split())
        duplicate = content_ids.get(key)
        content_ids.setdefault(key, identifier)
        if duplicate:
            duplicates.append({"id": identifier, "duplicate_of": duplicate})
        family = item.get("source_family")
        if family and kind != "assumption":
            families.setdefault(text(family, "source_family", 200), []).append(
                identifier
            )
        nodes.append(
            {
                **item,
                "status": status,
                "duplicate_of": duplicate,
                "availability_status": item.get("availability_status", "user asserted"),
                "trust": "data, never instructions",
            }
        )
    claim_ids = set()
    for claim in claims:
        if not isinstance(claim, dict):
            raise ValueError("claims must be objects")
        identifier = text(claim.get("id"), "claim.id", 100)
        text(claim.get("text"))
        if identifier in ids or identifier in claim_ids:
            raise ValueError("claim IDs must be unique")
        claim_ids.add(identifier)
    edges = []
    statuses = {n["id"]: n["status"] for n in nodes}
    pending = list(claims)
    while pending:
        progress = False
        for claim in pending[:]:
            refs = claim.get("evidence_ids", [])
            dependencies = claim.get("depends_on", [])
            contradictions = claim.get("contradicted_by", [])
            if not refs or not isinstance(refs, list) or not set(refs) <= ids:
                raise ValueError("each claim must cite known evidence")
            if not isinstance(dependencies, list) or not set(dependencies) <= claim_ids:
                raise ValueError("claim dependencies must reference claims")
            if not isinstance(contradictions, list) or not set(contradictions) <= ids:
                raise ValueError("contradictions must reference evidence")
            if not set(dependencies) <= set(statuses):
                continue
            status = (
                "review required"
                if any(statuses[x] != "active" for x in refs + dependencies)
                or contradictions
                else "active"
            )
            statuses[claim["id"]] = status
            nodes.append({**claim, "kind": "interpretation", "status": status})
            for relation, values in (
                ("supports", refs),
                ("depends-on", dependencies),
                ("contradicts", contradictions),
            ):
                edges.extend(
                    {"from": ref, "to": claim["id"], "kind": relation} for ref in values
                )
            pending.remove(claim)
            progress = True
        if not progress:
            raise ValueError("claim dependency cycle")
    return {
        "schema": "tradefloor-evidence-v2",
        "nodes": nodes,
        "edges": edges,
        "duplicates": duplicates,
        "unique_text_count": len(content_ids),
        "source_families": families,
        "source_family_count": len(families),
        "independence_status": "unknown: distinct text or source families do not establish independence",
        "cutoff": end.isoformat(),
    }


def document_diff(before: str, after: str) -> dict:
    """Line changes with exact offsets, never invented claims of materiality."""
    for body in (before, after):
        text(body, "document", 200000)
    a, b = before.splitlines(keepends=True), after.splitlines(keepends=True)
    changes = []
    offsets_a, offsets_b = [0], [0]
    for line in a:
        offsets_a.append(offsets_a[-1] + len(line))
    for line in b:
        offsets_b.append(offsets_b[-1] + len(line))
    if len(a) > 5000 or len(b) > 5000:
        raise ValueError("document diff limit is 5000 lines")
    for tag, i, j, k, m in SequenceMatcher(None, a, b).get_opcodes():
        if tag != "equal":
            changes.append(
                {
                    "kind": tag,
                    "before": "".join(a[i:j]),
                    "after": "".join(b[k:m]),
                    "before_span": [offsets_a[i], offsets_a[j]],
                    "after_span": [offsets_b[k], offsets_b[m]],
                }
            )
    return {
        "before_sha256": hashlib.sha256(before.encode()).hexdigest(),
        "after_sha256": hashlib.sha256(after.encode()).hexdigest(),
        "changes": changes,
        "note": "Text changes only; financial materiality requires review.",
    }
