"""Bounded user CSV imports and explicit provider captures with provenance."""
from __future__ import annotations

import csv
import io
import json
import os
import uuid

import pandas as pd

from . import data, lab, providers, research, runs, snapshots, validation as v
from .evidence import text
from .storage import canonical, connect


def source_settings(action="get", body=None, api_key=None):
    with connect(research.database()) as db:
        row = db.execute("SELECT body FROM config WHERE key='data-sources'").fetchone()
    saved = json.loads(row[0]) if row else {"id": uuid.uuid4().hex, "sec_contact": "", "key_env": "FRED_API_KEY", "has_key": False}
    if action == "save":
        if not isinstance(body, dict) or set(body) - {"sec_contact", "key_env"}:
            raise ValueError("Invalid source settings")
        updated = {**saved, **body}
        contact = updated["sec_contact"]
        if not isinstance(contact, str) or len(contact) > 250 or (contact and ("@" not in contact or "\n" in contact or "\r" in contact)):
            raise ValueError("SEC contact must contain an application name and contact email")
        import re
        if not isinstance(updated["key_env"], str) or (updated["key_env"] and not re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", updated["key_env"])):
            raise ValueError("Invalid ALFRED environment-variable name")
        if api_key is not None:
            if not isinstance(api_key, str) or not 1 <= len(api_key) <= 4096 or "\n" in api_key or "\r" in api_key:
                raise ValueError("Invalid ALFRED key")
            try:
                providers._vault().set_password(providers._service(), saved["id"], api_key)
            except Exception:
                raise ValueError("OS credential store unavailable; use an ALFRED environment key") from None
            updated.update(has_key=True, key_env="")
        with connect(research.database()) as db:
            db.execute("INSERT OR REPLACE INTO config VALUES ('data-sources',?)", (canonical(updated),))
        saved = updated
    elif action != "get":
        raise ValueError("Unsupported source settings action")
    return {**saved, "effective_sec_contact": os.environ.get("TRADEFLOOR_SEC_USER_AGENT") or saved["sec_contact"],
            "note": "Saved keys stay in the OS credential store; saved source settings do not fetch data."}


def source_credential(provider):
    p = source_settings()
    if provider == "sec":
        return p["effective_sec_contact"]
    return providers._secret(p)


def datasets(action="list", dataset_id=None, body=None):
    if action == "list":
        with connect(research.database()) as db:
            rows = db.execute("SELECT body FROM config WHERE key LIKE 'dataset:%' ORDER BY rowid DESC LIMIT 100").fetchall()
        return {"datasets": [{k: d[k] for k in ("id", "name", "symbol", "source", "available_at", "created_at", "sha256", "rows", "last_date")} for d in map(lambda r: json.loads(r[0]), rows)]}
    if action in ("import", "capture"):
        if not isinstance(body, dict):
            raise ValueError("Dataset fields required")
        symbol = v.symbol(body.get("symbol"))
        if action == "capture":
            df = data.history(symbol, data.parse_as_of(body.get("as_of")), years=5)
            source, available = "Yahoo Finance adjusted history captured now; not an archived vintage", research.now()
            rights = "Provider terms apply; redistribution not granted"
        else:
            raw = text(body.get("csv"), "CSV", 2_000_000).lstrip("\ufeff")
            reader = csv.DictReader(io.StringIO(raw))
            allowed = {"Date", "Open", "High", "Low", "Close", "Volume"}
            names = reader.fieldnames or []
            if len(set(names)) != len(names) or not {"Date", "Close"} <= set(names) or set(names) - allowed:
                raise ValueError("CSV needs unique Date,Close columns; optional Open,High,Low,Volume")
            rows = []
            for row in reader:
                if len(rows) >= 20000 or None in row or any(x is None or x == "" for x in row.values()):
                    raise ValueError("CSV is oversized or has missing/extra cells")
                rows.append({"Date": v.iso_date(row["Date"]), **{k: v.number(row[k], k, 0 if k == "Volume" else 1e-12) for k in names if k != "Date"}})
            if not 252 <= len(rows) <= 20000:
                raise ValueError("Supply between 252 and 20,000 daily observations")
            df = pd.DataFrame(rows).set_index("Date")
            df.index = pd.to_datetime(df.index)
            source = text(body.get("source"), "source", 1000)
            available = v.timestamp(body.get("available_at"))
            rights = text(body.get("rights"), "rights", 1000)
        payload = snapshots.frame(df)
        snapshots.restore(payload)
        if {"High", "Low"} <= set(df.columns):
            if (df.High < df.Low).any() or (df.Close > df.High).any() or (df.Close < df.Low).any():
                raise ValueError("High/Low must bound Close on every row")
            if "Open" in df and ((df.Open > df.High).any() or (df.Open < df.Low).any()):
                raise ValueError("High/Low must bound Open on every row")
        payload.update(symbol=symbol, adjustment_basis=text(body.get("adjustment_basis", "User-supplied basis; verify before settlement"), "adjustment basis", 1000), rights=rights)
        item = {"id": uuid.uuid4().hex, "name": text(body.get("name"), "name", 100), "symbol": symbol,
                "source": source, "available_at": available, "created_at": research.now(), "snapshot": payload,
                "rows": len(df), "last_date": str(df.index[-1].date()), "availability_status": "Supplied or capture-time metadata; not independently historically verified"}
        item["sha256"] = runs.digest(item)
        with connect(research.database()) as db:
            db.execute("INSERT INTO config VALUES (?,?)", ("dataset:" + item["id"], canonical(item)))
        return item
    runs.identity(dataset_id)
    with connect(research.database()) as db:
        row = db.execute("SELECT body FROM config WHERE key=?", ("dataset:" + dataset_id,)).fetchone()
    if not row:
        raise ValueError("Dataset not found")
    item = json.loads(row[0])
    if runs.digest({k: val for k, val in item.items() if k != "sha256"}) != item["sha256"]:
        raise ValueError("Dataset integrity check failed")
    if action == "get":
        return item
    if action == "scenario":
        body = body or {}
        if not {"High", "Low"} <= set(item["snapshot"]["columns"]):
            raise ValueError("Scenario analytics require supplied High and Low columns; Close-only datasets remain available for export")
        from .evidence import stamp
        cutoff = stamp(item["last_date"] + "T23:59:59Z")
        dated = stamp(item["available_at"]) <= cutoff
        evidence = [{"id": "D1", "kind": "measurement" if dated else "assumption", "text": item["source"] + ("" if dated else "; captured after the price cutoff, historical availability unverified"), "source": item["source"],
                     "published_at": item["available_at"], "available_at": item["available_at"]},
                    {"id": "D2", "kind": "assumption", "text": text(body.get("hypothesis"), "hypothesis", 2000)}]
        if not dated:
            evidence[0].pop("published_at")
            evidence[0].pop("available_at")
            evidence[0]["availability_status"] = "not known available at cutoff; current capture used only as an explicit research assumption"
        result = lab.simulate(case=body.get("case", "earnings"), worlds=300, price_snapshot={**item["snapshot"], "symbol": item["symbol"]}, evidence=evidence,
                              claims=[{"id": "H1", "text": body["hypothesis"], "evidence_ids": ["D1", "D2"]}])
        return {"result": result, "bundle_json": canonical(runs.read(result["run"]["run_id"]))}
    raise ValueError("Unsupported dataset action")
