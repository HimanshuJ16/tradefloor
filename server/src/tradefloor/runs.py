"""Immutable local experiment bundles with content hashes and safe import."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import settings
from .storage import canonical


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def root() -> Path:
    p = settings.home() / "runs"
    p.mkdir(exist_ok=True)
    return p


def identity(run_id: str) -> str:
    if not re.fullmatch(r"[a-f0-9]{32}", str(run_id)):
        raise ValueError("run_id must be a 32-character hexadecimal ID")
    return run_id


def create(
    kind: str, request: dict, inputs: dict, result: dict, parent: str | None = None
) -> dict:
    if parent:
        read(parent)
    run_id = uuid.uuid4().hex
    versions = {}
    for pkg in (
        "tradefloor",
        "numpy",
        "pandas",
        "yfinance",
        "mcp",
        "exchange-calendars",
    ):
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            versions[pkg] = "not installed"
    code_hash = digest(
        {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(__file__).parent.glob("*.py"))
        }
    )
    bundle = {
        "schema": "tradefloor-run-v1",
        "id": run_id,
        "kind": kind,
        "parent": parent,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "request": request,
        "inputs": inputs,
        "result": result,
        "runtime": {
            "python": platform.python_version(),
            "packages": versions,
            "source_sha256": code_hash,
        },
        "integrity_note": "Local content hash detects edits; it is not an external timestamp or proof of predictive skill.",
    }
    bundle["sha256"] = digest(bundle)
    folder = root() / run_id
    folder.mkdir()
    (folder / "bundle.json").write_text(canonical(bundle), encoding="utf-8")
    return {
        "run_id": run_id,
        "sha256": bundle["sha256"],
        "path": str(folder / "bundle.json"),
    }


def verify(bundle: dict) -> dict:
    if not isinstance(bundle, dict) or bundle.get("schema") != "tradefloor-run-v1":
        raise ValueError("unsupported run bundle")
    identity(bundle.get("id"))
    if len(canonical(bundle).encode("utf-8")) > 20_000_000:
        raise ValueError("bundle exceeds 20 MB")
    if not all(
        k in bundle
        for k in (
            "request",
            "inputs",
            "result",
            "runtime",
            "created_at",
            "kind",
            "parent",
        )
    ):
        raise ValueError("bundle is missing required fields")
    body = {k: v for k, v in bundle.items() if k != "sha256"}
    if digest(body) != bundle.get("sha256"):
        raise ValueError("bundle integrity check failed")
    from . import schemas
    schemas.bundle(bundle)
    return bundle


def read(run_id: str) -> dict:
    return verify(
        json.loads(
            (root() / identity(run_id) / "bundle.json").read_text(encoding="utf-8")
        )
    )


def import_bundle(bundle: dict) -> dict:
    verify(bundle)
    folder = root() / bundle["id"]
    folder.mkdir(exist_ok=True)
    target = folder / "bundle.json"
    if target.exists():
        if read(bundle["id"])["sha256"] != bundle["sha256"]:
            raise ValueError("run ID already exists with different content")
    else:
        with target.open("x", encoding="utf-8") as f:
            f.write(canonical(bundle))
    return {"run_id": bundle["id"], "sha256": bundle["sha256"], "path": str(target)}


def desk_inputs() -> dict:
    repository = Path(__file__).parents[3]
    paths = [
        repository / "rules" / "tradefloor.md",
        *sorted((repository / "roles").glob("*.md")),
    ]
    prompts = {
        str(p.relative_to(repository)): p.read_text(encoding="utf-8")
        for p in paths
        if p.is_file()
    }
    return {
        "settings": settings.effective(),
        "prompt_sources": prompts,
        "prompt_capture_status": "repository sources captured"
        if prompts
        else "source prompts unavailable in installed wheel; host must supply its prompt receipt",
    }


def finalize(run_id: str, decision: dict) -> dict:
    original = read(run_id)
    if original["kind"] not in ("analyze", "scout", "swarm-desk"):
        raise ValueError("only desk workspaces can be finalized")
    workspace = (root() / identity(run_id) / "reports").resolve()
    reports = {}
    total = 0
    for p in workspace.iterdir():
        if not p.is_file():
            continue
        if p.is_symlink() or workspace not in p.resolve().parents:
            raise ValueError("report must remain inside its workspace")
        if p.suffix not in (".md", ".json", ".txt"):
            continue
        total += p.stat().st_size
        if total > 2_000_000 or len(reports) >= 100:
            raise ValueError("report snapshot exceeds 2 MB/100 files")
        content = p.read_text(encoding="utf-8")
        reports[p.name] = {
            "content": content,
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        }
    if not reports:
        raise ValueError("workspace has no reports to finalize")
    return create(
        "desk-report",
        original["request"],
        {**original["inputs"], "reports": reports},
        decision,
        run_id,
    )
