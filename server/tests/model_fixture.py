"""Loopback-only synthetic SSE endpoint for manual browser QA; never a real model."""
import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        prompt = body["messages"][-1]["content"]
        if prompt == "Connection test; no research data.":
            output = "connected"
        else:
            p = json.loads(prompt)
            c = p["frozen_context"]
            if not p.get("requested_tool_results"):
                output = json.dumps({"summary": "Synthetic QA adapter requests frozen evidence.", "tool_requests": ["inspect_evidence", "baseline_forecasts"]})
            else:
                prior = c["baseline_forecasts"]["quant"]
                adjusted = dict(prior)
                delta = .01 if body["model"] == "qa-up" else -.01
                adjusted["up"] += delta
                adjusted["down"] -= delta
                eid = c["inspect_evidence"][0]["id"]
                output = json.dumps({"summary": "Synthetic QA adapter: inspect persistence and absorption. Not investment advice. Verify before acting.",
                    "claims": [{"id": "C1", "text": "The event reaction is an explicit assumption.", "evidence_ids": [eid]}],
                    "probabilities": adjusted, "adjustments": [{"class": "up", "delta": delta, "reason": "Synthetic test adjustment", "evidence_ids": [eid]},
                    {"class": "down", "delta": -delta, "reason": "Synthetic test adjustment", "evidence_ids": [eid]}], "abstain": False,
                    "assumptions": ["Persistence is supplied rather than measured"], "objections": ["The event could already be priced in"],
                    "resolutions": [{"question": "Does attention persist?", "evidence_needed": "Dated attention observations", "test": "Compare measured decay against the supplied half-life"}], "tool_requests": []})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        try:
            for i in range(0, len(output), 40):
                chunk = {"choices": [{"delta": {"content": output[i:i+40]}}]}
                self.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())
                self.wfile.flush()
                time.sleep(.08 if body["model"] != "qa-slow" else .5)
            self.wfile.write(b'data: {"choices":[],"usage":{"prompt_tokens":300,"completion_tokens":200}}\n\ndata: [DONE]\n\n')
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=9909)
    port = parser.parse_args().port
    print(f"SYNTHETIC QA endpoint at http://127.0.0.1:{port}/v1; qa-up/qa-down/qa-slow", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
