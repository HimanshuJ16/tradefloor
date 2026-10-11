"""Local dated data receipts. Never relabel today's screener as a historical universe."""

from __future__ import annotations
import json
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from . import runs, settings
from .storage import canonical


def frame(df: pd.DataFrame) -> dict:
    return {
        "schema": "ohlcv-v1",
        "index": [x.isoformat() for x in df.index],
        "columns": list(df.columns),
        "rows": [
            [None if pd.isna(v) else float(v) for v in row] for row in df.to_numpy()
        ],
        "adjustment_basis": "provider adjusted at capture time",
        "rights": "local personal research; redistribution not granted",
    }


def restore(payload: dict) -> pd.DataFrame:
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != "ohlcv-v1"
        or not 1 <= len(payload.get("rows", [])) <= 20000
    ):
        raise ValueError("unsupported or oversized price snapshot")
    df = pd.DataFrame(
        payload["rows"],
        columns=payload["columns"],
        index=pd.to_datetime(payload["index"]),
    )
    if (
        "Close" not in df
        or df.columns.has_duplicates
        or df.index.has_duplicates
        or df.index.hasnans
        or not df.index.is_monotonic_increasing
    ):
        raise ValueError("snapshot needs ordered unique timestamps and Close")
    if set(df.columns) - {
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
        "Dividends",
        "Stock Splits",
    }:
        raise ValueError("unsupported snapshot columns")
    if (
        len(payload["index"]) != len(payload["rows"])
        or not np.isfinite(df.to_numpy(dtype=float)).all()
    ):
        raise ValueError(
            "snapshot values must be finite and timestamps must match rows"
        )
    if (df["Close"] <= 0).any():
        raise ValueError("Close must be positive")
    return df


def capture_universe(market: str, universe: dict) -> dict:
    receipt = {
        "market": market,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "universe": universe,
        "point_in_time": True,
        "rights": "local personal research",
    }
    # A different capture is a different immutable receipt, including corrected metadata.
    identifier = runs.digest(receipt)
    folder = settings.home() / "universes"
    folder.mkdir(exist_ok=True)
    (folder / f"{identifier}.json").write_text(canonical(receipt), encoding="utf-8")
    return {"id": identifier, **receipt}


def historical_universe(market: str, cutoff: datetime) -> dict | None:
    folder = settings.home() / "universes"
    candidates = []
    for p in folder.glob("*.json") if folder.exists() else []:
        r = json.loads(p.read_text(encoding="utf-8"))
        if runs.digest(r) != p.stem:
            raise ValueError("universe receipt integrity check failed")
        if r["market"] == market and datetime.fromisoformat(r["captured_at"]) <= cutoff:
            candidates.append(r)
    return max(candidates, key=lambda r: r["captured_at"]) if candidates else None
