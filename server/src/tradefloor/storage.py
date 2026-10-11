"""Transactional local storage; JSON is an interchange format, not a concurrent database."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def canonical(value) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


@contextmanager
def connect(path: Path):
    db = sqlite3.connect(path, timeout=15)
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA busy_timeout=15000")
        db.execute(
            "CREATE TABLE IF NOT EXISTS records (seq INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL, body TEXT NOT NULL)"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS settlements (id TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, body TEXT NOT NULL)"
        )
        db.execute("BEGIN IMMEDIATE")
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
