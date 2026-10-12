"""Single-process worker with SQLite leases, idempotency and cooperative cancellation."""

from __future__ import annotations
import json
import threading
import time
import uuid
from . import research, validation as v
from .storage import canonical, connect

ALLOWED = {"challenge", "investigate", "arena", "fetch", "scenario", "project_scenario", "model_session", "dataset_capture"}


def _table(db):
    db.execute(
        "CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, token TEXT, idem TEXT UNIQUE, payload TEXT, state TEXT, updated REAL, progress TEXT, result TEXT, error TEXT)"
    )


def submit(kind, arguments, idempotency_key):
    if kind not in ALLOWED or not isinstance(arguments, dict):
        raise ValueError("unsupported research job")
    from .evidence import text

    text(idempotency_key, "idempotency_key", 120)
    raw = canonical({"kind": kind, "arguments": arguments})
    if len(raw.encode()) > 2_000_000:
        raise ValueError("job arguments exceed 2 MB")
    identifier = uuid.uuid4().hex
    with connect(research.database()) as db:
        _table(db)
        existing = db.execute(
            "SELECT id,payload FROM jobs WHERE idem=?", (idempotency_key,)
        ).fetchone()
        if existing:
            if existing[1] != raw:
                raise ValueError("idempotency key reused with different arguments")
            identifier = existing[0]
        else:
            active = db.execute(
                "SELECT COUNT(*) FROM jobs WHERE state IN ('queued','running')"
            ).fetchone()[0]
            if active >= 20:
                raise ValueError("job queue is full (20)")
            db.execute(
                "INSERT INTO jobs VALUES (?,NULL,?,?,'queued',?,'{}',NULL,NULL)",
                (identifier, idempotency_key, raw, time.time()),
            )
    return get(identifier)


def get(identifier=None):
    with connect(research.database()) as db:
        _table(db)
        rows = db.execute(
            "SELECT id,payload,state,updated,progress,result,error FROM jobs"
            + (" WHERE id=?" if identifier else " ORDER BY updated DESC LIMIT 50"),
            (identifier,) if identifier else (),
        ).fetchall()
    items = [
        {
            "id": r[0],
            "kind": json.loads(r[1])["kind"],
            "state": r[2],
            "updated": r[3],
            "progress": json.loads(r[4]),
            "result": json.loads(r[5]) if r[5] else None,
            "error": r[6],
        }
        for r in rows
    ]
    if identifier and not items:
        raise ValueError("job not found")
    return items[0] if identifier else {"jobs": items}


def cancel(identifier):
    with connect(research.database()) as db:
        _table(db)
        db.execute(
            "UPDATE jobs SET state='cancelled', updated=? WHERE id=? AND state IN ('queued','running')",
            (time.time(), identifier),
        )
    return get(identifier)


def execute(kind, arguments, progress=None):
    from . import arena, lab, timeline

    if kind == "model_session":
        from . import desk
        return desk.execute(**arguments, progress=progress)
    if kind == "dataset_capture":
        from . import datahub
        return datahub.datasets("capture", body=arguments)

    if kind == "challenge":
        return research.challenge(**arguments, progress=progress)
    if kind == "investigate":
        return research.investigate(**arguments)
    if kind == "arena":
        return arena.forecast_run(**arguments)
    if kind == "fetch":
        return timeline.fetch(**arguments)
    if kind == "project_scenario":
        return research.project_scenario(**arguments)
    if kind == "scenario":
        if set(arguments) - {
            "case",
            "sentiment",
            "persistence",
            "retail_weight",
            "seed",
            "worlds",
            "sensitivity",
            "price_snapshot",
            "evidence",
        }:
            raise ValueError("unsupported scenario argument")
        return lab.simulate(**arguments)
    raise ValueError("unsupported job")


class Worker:
    def __init__(self):
        self.stop = threading.Event()
        self.last_error = None
        self.thread = threading.Thread(
            target=self.loop, daemon=True, name="tradefloor-research"
        )

    def start(self):
        self.thread.start()
        return self

    def loop(self):
        while not self.stop.is_set():
            try:
                self.once()
            except Exception as exc:
                self.last_error = str(exc)
            self.stop.wait(0.25)

    def once(self):
        token = uuid.uuid4().hex
        with connect(research.database()) as db:
            _table(db)
            db.execute(
                "UPDATE jobs SET state='queued',token=NULL WHERE state='running' AND updated<?",
                (time.time() - 120,),
            )
            row = db.execute(
                "SELECT id,payload FROM jobs WHERE state='queued' ORDER BY updated LIMIT 1"
            ).fetchone()
            if not row:
                return
            db.execute(
                "UPDATE jobs SET state='running',token=?,updated=? WHERE id=?",
                (token, time.time(), row[0]),
            )

        def progress(done, total):
            v.integer(done, "done", 0, 100000)
            v.integer(total, "total", 1, 100000)
            with connect(research.database()) as db:
                state = db.execute(
                    "SELECT state,token FROM jobs WHERE id=?", (row[0],)
                ).fetchone()
                if state != ("running", token) or self.stop.is_set():
                    raise InterruptedError("job cancelled or lease replaced")
                db.execute(
                    "UPDATE jobs SET progress=?,updated=? WHERE id=? AND token=?",
                    (
                        canonical({"done": done, "total": total}),
                        time.time(),
                        row[0],
                        token,
                    ),
                )

        heartbeat_stop = threading.Event()

        def heartbeat():
            while not heartbeat_stop.wait(15):
                try:
                    with connect(research.database()) as db:
                        db.execute(
                            "UPDATE jobs SET updated=? WHERE id=? AND state='running' AND token=?",
                            (time.time(), row[0], token),
                        )
                except Exception as exc:
                    self.last_error = str(exc)

        heart = threading.Thread(target=heartbeat, daemon=True)
        heart.start()
        try:
            payload = json.loads(row[1])
            progress(0, 1)
            result = execute(payload["kind"], payload["arguments"], progress)
            progress(1, 1)
            state, error = "completed", None
        except InterruptedError as exc:
            result, state, error = None, "cancelled", str(exc)
        except Exception as exc:
            result, state, error = None, "failed", str(exc)
        finally:
            heartbeat_stop.set()
            heart.join(timeout=1)
        with connect(research.database()) as db:
            db.execute(
                "UPDATE jobs SET state=?,result=?,error=?,updated=? WHERE id=? AND state='running' AND token=?",
                (state, canonical(result), error, time.time(), row[0], token),
            )
