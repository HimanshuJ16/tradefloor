"""Transactional local storage; JSON is an interchange format, not a concurrent database."""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

_initialization = threading.RLock()


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
        db.execute("PRAGMA busy_timeout=15000")
        # Changing journal mode concurrently on a brand-new database can bypass
        # SQLite's busy handler. Serialize setup and avoid resetting an existing WAL.
        with _initialization:
            if db.execute("PRAGMA journal_mode").fetchone()[0] != "wal":
                db.execute("PRAGMA journal_mode=WAL")
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
