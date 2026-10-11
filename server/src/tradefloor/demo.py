"""Loopback-only scenario UI and standalone, synthetic demo export."""

from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from . import lab, runs
from .storage import canonical

ASSETS = Path(__file__).parent / "assets"
PRESETS = {
    "original": {},
    "fades": {"persistence": 1},
    "persistent": {"persistence": 20},
    "small-retail": {"retail_weight": 0.1},
    "large-retail": {"retail_weight": 0.5},
    "reverse": {"sentiment": -0.6},
    "neutral": {"sentiment": 0},
}


def document(embedded: dict | None = None) -> str:
    html = (ASSETS / "index.html").read_text(encoding="utf-8")
    css = (ASSETS / "app.css").read_text(encoding="utf-8")
    js = (ASSETS / "app.js").read_text(encoding="utf-8")
    payload = (
        canonical(embedded or {})
        .replace("<", "\\u003c")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    return (
        html.replace("/*STYLE*/", css)
        .replace("/*DATA*/", f"window.DEMO_DATA={payload};")
        .replace("/*APP*/", js)
    )


def workspace_document(embedded: dict | None = None) -> str:
    html = (ASSETS / "workspace.html").read_text(encoding="utf-8")
    payload = canonical(embedded or {}).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return (html.replace("/*STYLE*/", (ASSETS / "workspace.css").read_text(encoding="utf-8"))
            .replace("/*DATA*/", "window.DEMO_DATA=" + payload + ";")
            .replace("/*APP*/", (ASSETS / "workspace.js").read_text(encoding="utf-8")))


def workspace_action(body: dict) -> dict:
    from . import research_tools, research, runs, jobs
    action = body.get("action")
    arguments = body.get("arguments", {})
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")
    if action == "scoreboard":
        from .registry import scoreboard
        return scoreboard()
    if action == "load_run":
        b = runs.read(arguments["run_id"])
        if b["kind"] != "scenario":
            raise ValueError("workspace displays scenario receipts")
        return {"result": {**b["result"], "run": {"run_id": b["id"], "sha256": b["sha256"]}}, "bundle_json": canonical(b)}
    if action == "fork":
        r = lab.fork(arguments["run_id"], arguments["overrides"])
        return {"result": r, "bundle_json": canonical(runs.read(r["run"]["run_id"]))}
    if action == "project_export":
        return research.export_project(**arguments)
    if action == "job_result":
        return jobs.get(arguments["job_id"])
    if action not in research_tools.TOOLS:
        raise ValueError("unknown workspace action")
    return research_tools.TOOLS[action](**arguments)


def response_for(body: dict) -> dict:
    action = body.get("action", "simulate")
    if action == "import":
        bundle = (
            json.loads(body["bundle_json"])
            if body.get("bundle_json") is not None
            else body["bundle"]
        )
        runs.verify(bundle)
        if bundle["kind"] != "scenario":
            raise ValueError("the demo displays scenario bundles only")
        receipt = runs.import_bundle(bundle)
        b = runs.read(receipt["run_id"])
        if b["kind"] != "scenario":
            raise ValueError("the demo displays scenario bundles only")
        return {"result": {**b["result"], "run": receipt}, "bundle_json": canonical(b)}
    case, preset = body.get("case", "earnings"), body.get("preset", "original")
    if preset not in PRESETS:
        raise ValueError("unknown assumption preset")
    overrides = dict(PRESETS[preset])
    if preset == "reverse":
        parent_case = (
            runs.read(body["run_id"])["request"]["case"] if action == "fork" else case
        )
        overrides["sentiment"] = -lab.CASES[parent_case]["sentiment"]
    if action == "fork":
        result = lab.fork(body["run_id"], overrides)
    elif action == "simulate":
        result = lab.simulate(case, worlds=300, **overrides)
    else:
        raise ValueError("unknown demo action")
    return {
        "result": result,
        "bundle_json": canonical(runs.read(result["run"]["run_id"])),
    }


def make_server(port: int = 8765) -> ThreadingHTTPServer:
    gate = threading.BoundedSemaphore(1)

    class Handler(BaseHTTPRequestHandler):
        server_version = "TradefloorDemo"

        def send(self, status: int, payload: bytes, mime: str = "application/json"):
            self.send_response(status)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
            )
            self.end_headers()
            self.wfile.write(payload)

        def valid_host(self):
            expected = f"127.0.0.1:{self.server.server_port}"
            return self.headers.get("Host") == expected

        def do_GET(self):
            if not self.valid_host():
                return self.send(403, b'{"error":"invalid host"}')
            if urlsplit(self.path).path in ("/", "/workspace"):
                return self.send(200, workspace_document().encode("utf-8"), "text/html")
            if urlsplit(self.path).path == "/lab":
                return self.send(200, document().encode("utf-8"), "text/html")
            if self.path == "/health":
                return self.send(
                    200, b'{"status":"ok","mode":"synthetic loopback demo"}'
                )
            self.send(404, b'{"error":"not found"}')

        def do_POST(self):
            expected = f"http://127.0.0.1:{self.server.server_port}"
            if not self.valid_host() or self.headers.get("Origin") != expected:
                return self.send(
                    403, b'{"error":"same-origin browser requests required"}'
                )
            if (
                self.path not in ("/api/scenario", "/api/workspace")
                or self.headers.get("Content-Type", "").split(";")[0]
                != "application/json"
            ):
                return self.send(400, b'{"error":"JSON scenario request required"}')
            try:
                length = int(self.headers.get("Content-Length", "0"))
                limit = 20_000_000 if self.path == "/api/workspace" else 2_000_000
                if not 0 < length <= limit:
                    return self.send(
                        413, b'{"error":"request exceeds endpoint size limit or is empty"}'
                    )
                self.connection.settimeout(10)
                body = json.loads(
                    self.rfile.read(length),
                    parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)),
                )
                if not isinstance(body, dict):
                    raise ValueError("request must be an object")
                if not gate.acquire(blocking=False):
                    return self.send(
                        429, b'{"error":"another scenario is running; retry shortly"}'
                    )
                try:
                    result = workspace_action(body) if self.path == "/api/workspace" else response_for(body)
                finally:
                    gate.release()
                self.send(200, canonical(result).encode("utf-8"))
            except (ValueError, KeyError, TypeError, OSError) as e:
                self.send(400, canonical({"error": str(e)}).encode("utf-8"))

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    from .jobs import Worker
    server.research_worker = Worker().start()
    original_close = server.server_close
    def close():
        server.research_worker.stop.set()
        server.research_worker.thread.join(timeout=2)
        original_close()
    server.server_close = close
    return server


def export(target: Path):
    embedded = {}
    for case in lab.CASES:
        original = response_for({"case": case})
        original["result"]["run"].pop("path", None)
        embedded[f"{case}:original"] = original
        for preset in PRESETS:
            if preset != "original":
                fork = response_for(
                    {
                        "action": "fork",
                        "case": case,
                        "preset": preset,
                        "run_id": original["result"]["run"]["run_id"],
                    }
                )
                fork["result"]["run"].pop("path", None)
                embedded[f"{case}:{preset}"] = fork
        print(f"Built {case}: seven frozen assumption sets", flush=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(workspace_document(embedded), encoding="utf-8")
    print(f"Standalone synthetic demo: {target.resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--export",
        type=Path,
        help="Write a standalone HTML demo; all examples are synthetic",
    )
    args = parser.parse_args()
    if args.export:
        export(args.export)
        return
    server = make_server(args.port)
    print(
        f"Tradefloor scenario lab: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
