"""Immutable vintages. Unknown availability never becomes historical eligibility."""

from __future__ import annotations

import json
import os
import re
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from datetime import datetime, timezone
from . import runs, settings, validation as v
from .evidence import stamp, text
from .storage import canonical, connect

_lock = threading.Lock()
_last = 0.0


def ingest(records):
    if not isinstance(records, list) or not 1 <= len(records) <= 5000:
        raise ValueError("ingest requires 1..5000 records")
    rows = []
    for raw in records:
        r = dict(raw)
        for key in ("series", "observation_key", "source", "rights"):
            text(r.get(key), key, 500)
        if "value" not in r:
            raise ValueError("observation requires value")
        from .schemas import bounded

        bounded(r["value"])
        for key in ("effective_at", "retrieved_at"):
            r[key] = stamp(r.get(key)).isoformat()
        for key in ("published_at", "available_at"):
            r[key] = stamp(r[key]).isoformat() if r.get(key) else None
        if (
            r["available_at"]
            and r["published_at"]
            and stamp(r["available_at"]) < stamp(r["published_at"])
        ):
            raise ValueError("availability precedes publication")
        r["availability_status"] = r.get("availability_status", "user asserted")
        r["id"] = runs.digest({k: value for k, value in r.items() if k != "id"})
        rows.append(r)
    with connect(settings.home() / "timeline.sqlite3") as db:
        for r in rows:
            db.execute(
                "INSERT OR IGNORE INTO records(id,body) VALUES (?,?)",
                (r["id"], canonical(r)),
            )
    return {"records": rows, "count": len(rows)}


def query(cutoff, series=None):
    end = stamp(cutoff)
    with connect(settings.home() / "timeline.sqlite3") as db:
        rows = [json.loads(r[0]) for r in db.execute("SELECT body FROM records")]
    selected, excluded = {}, {"unknown_availability": 0, "later_availability": 0}
    for r in rows:
        if series and r["series"] != series:
            continue
        if not r["available_at"]:
            excluded["unknown_availability"] += 1
            continue
        if stamp(r["available_at"]) > end or (
            r["published_at"] and stamp(r["published_at"]) > end
        ):
            excluded["later_availability"] += 1
            continue
        key = (r["series"], r["observation_key"], r["source"])
        old = selected.get(key)
        if old is None or (
            stamp(r["available_at"]),
            stamp(r["retrieved_at"]),
            r["id"],
        ) > (stamp(old["available_at"]), stamp(old["retrieved_at"]), old["id"]):
            selected[key] = r
    records = sorted(
        selected.values(),
        key=lambda r: (r["series"], r["observation_key"], r["source"]),
    )
    return {
        "schema": "tradefloor-timeline-v1",
        "cutoff": end.isoformat(),
        "records": records,
        "snapshot_sha256": runs.digest(records),
        "excluded": excluded,
        "note": "Availability metadata is source/user asserted. Frozen snapshot hashes preserve a prior query; later ingestion can add previously missing records.",
    }


def _fetch(url, headers=None):
    global _last
    with _lock:
        delay = 0.25 - (time.monotonic() - _last)
        if delay > 0:
            time.sleep(delay)
        _last = time.monotonic()
        try:
            with urlopen(Request(url, headers=headers or {}), timeout=15) as response:
                raw = response.read(5_000_001)
            if len(raw) > 5_000_000:
                raise ValueError("provider payload exceeds 5 MB")
            return json.loads(raw)
        except Exception as exc:
            # URLs can contain a FRED key; never expose exception URLs.
            raise ValueError(
                f"provider request failed ({type(exc).__name__}); check credentials, rate limits and connectivity"
            ) from None


def fetch(provider, identifier, vintage=None):
    from .datahub import source_credential
    now = datetime.now(timezone.utc).isoformat()
    records = []
    if provider == "sec":
        if not re.fullmatch(r"\d{1,10}", identifier):
            raise ValueError("SEC identifier must be a CIK with up to 10 digits")
        agent = os.environ.get("TRADEFLOOR_SEC_USER_AGENT") or source_credential("sec")
        if "@" not in agent or len(agent) > 250:
            raise ValueError(
                "set TRADEFLOOR_SEC_USER_AGENT to your application name and contact email"
            )
        cik = identifier.zfill(10)
        data = _fetch(
            f"https://data.sec.gov/submissions/CIK{cik}.json", {"User-Agent": agent}
        )
        recent = data.get("filings", {}).get("recent", {})
        for i, accession in enumerate(recent.get("accessionNumber", [])):
            accepted = recent.get("acceptanceDateTime", [])[i]
            if not accepted:
                continue
            accepted = stamp(accepted).isoformat()
            form = recent["form"][i]
            records.append(
                {
                    "series": "SEC:" + cik,
                    "observation_key": accession,
                    "source": "SEC EDGAR submissions",
                    "effective_at": accepted,
                    "published_at": accepted,
                    "available_at": accepted,
                    "retrieved_at": now,
                    "value": {
                        "form": form,
                        "accession": accession,
                        "primary_document": recent["primaryDocument"][i],
                        "company": data.get("name", ""),
                        "filing_date": recent["filingDate"][i],
                    },
                    "availability_status": "provider acceptance timestamp; dissemination latency not measured",
                    "rights": "SEC public filing metadata; source terms apply",
                }
            )
        scope = "Recent submissions metadata only; older submission files and filing facts are not inferred."
    elif provider == "alfred":
        if not re.fullmatch(r"[A-Za-z0-9_]{1,80}", identifier):
            raise ValueError("invalid FRED series ID")
        vintage = v.iso_date(vintage, "vintage")
        key = os.environ.get("FRED_API_KEY") or source_credential("alfred")
        if not key:
            raise ValueError("set FRED_API_KEY to fetch ALFRED vintages")
        data = _fetch(
            "https://api.stlouisfed.org/fred/series/observations?"
            + urlencode(
                {
                    "series_id": identifier,
                    "api_key": key,
                    "file_type": "json",
                    "realtime_start": vintage,
                    "realtime_end": vintage,
                    "output_type": 1,
                    "limit": 5000,
                }
            )
        )
        for observation in data.get("observations", []):
            if observation["value"] == ".":
                continue
            available = vintage + "T23:59:59+00:00"
            records.append(
                {
                    "series": "ALFRED:" + identifier,
                    "observation_key": observation["date"],
                    "source": "ALFRED vintage",
                    "effective_at": observation["date"] + "T00:00:00+00:00",
                    "published_at": None,
                    "available_at": available,
                    "retrieved_at": now,
                    "value": v.number(observation["value"], "value"),
                    "vintage": vintage,
                    "availability_status": "date-level vintage, conservatively eligible at end of UTC day; not intraday certified",
                    "rights": "FRED series-specific source terms; redistribution not assumed",
                }
            )
        scope = "At most 5000 observations from requested vintage; no intraday availability claim."
    else:
        raise ValueError("provider must be sec or alfred")
    if not records:
        raise ValueError("provider returned no usable observations")
    return {**ingest(records), "provider": provider, "scope": scope}
