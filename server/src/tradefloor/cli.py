"""Command-line access to every tradefloor tool, for agents with a shell but no MCP.

    tradefloor list
    tradefloor direction_forecast symbol=^NSEI horizon=1m
    tradefloor scan symbols=AAPL,MSFT,INFY.NS horizon=1m
    tradefloor journal_record --json '{"entry": {...}}'

Output is the same JSON object the MCP tool returns. Exit code 1 when it holds "error".
"""

from __future__ import annotations

import inspect
import json
import sys
import types
import typing
from pathlib import Path

from . import server

TOOLS = {
    "quick_direction": server.quick_direction,
    "resolve_symbol": server.resolve_symbol,
    "list_markets": server.list_markets,
    "technical_report": server.technical_report,
    "direction_forecast": server.direction_forecast,
    "fundamentals": server.fundamentals,
    "news": server.news,
    "sentiment_signals": server.sentiment_signals,
    "macro_context": server.macro_context,
    "trade_plan": server.trade_plan,
    "scan": server.scan,
    "intraday_scan": server.intraday_scan,
    "swarm_roster": server.swarm_roster,
    "swarm_simulate": server.swarm_simulate,
    "journal_record": server.journal_record,
    "journal_review": server.journal_review,
    "settings": server.settings_tool,
    **{name: getattr(server, name) for name in (
        "scenario_lab", "scenario_fork", "run_bundle", "run_replay", "run_begin", "run_finalize", "evidence_audit",
        "decision_validate", "falsification_check", "forecast_evaluation", "learning_review",
        "portfolio_stress", "experiment_record", "experiment_settle", "experiment_scoreboard", "experiment_capture", "experiment_mature", "journal_export", "market_sandbox")},
}
TOOLS.update(server.research_tools.TOOLS)


def _cast(fn, name: str, raw: str):
    hint = typing.get_type_hints(fn).get(name, str)
    if typing.get_origin(hint) in (typing.Union, types.UnionType):  # Optional[X] / X | None
        hint = next(a for a in typing.get_args(hint) if a is not type(None))
    kind = typing.get_origin(hint) or hint
    if kind is list:
        if raw.lstrip().startswith("["):
            return json.loads(raw)
        return [s.strip() for s in raw.split(",") if s.strip()]
    if kind is bool:
        if raw.lower() not in ("1", "true", "yes", "y", "0", "false", "no", "n"):
            raise ValueError(f"invalid boolean {raw!r}")
        return raw.lower() in ("1", "true", "yes", "y")
    if kind is int:
        return int(raw)
    if kind is float:
        return float(raw)
    if kind is dict:
        return json.loads(raw)
    return raw


def usage() -> str:
    lines = ["usage: tradefloor <tool> [key=value ...] [--json '{...}']", "", "tools:"]
    for name, fn in TOOLS.items():
        params = ", ".join(inspect.signature(fn).parameters)
        doc = (fn.__doc__ or "").strip().split("\n")[0]
        lines.append(f"  {name}({params})\n      {doc}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help", "help", "list"):
        print(usage())
        return 0
    name, rest = argv[0], argv[1:]
    fn = TOOLS.get(name)
    if fn is None:
        print(json.dumps({"error": f"unknown tool {name!r}; run `tradefloor list`"}))
        return 1
    kwargs: dict = {}
    i = 0
    try:
        while i < len(rest):
            tok = rest[i]
            if tok in ("--json", "--file") and i + 1 < len(rest):
                raw = Path(rest[i + 1]).read_text(encoding="utf-8-sig") if tok == "--file" else rest[i + 1]
                parsed = json.loads(raw, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(f"nonfinite {v}")))
                if not isinstance(parsed, dict):
                    raise ValueError("arguments JSON must be an object")
                kwargs.update(parsed)
                i += 2
                continue
            if "=" not in tok:
                raise ValueError(f"expected key=value, got {tok!r}")
            k, v = tok.split("=", 1)
            kwargs[k] = _cast(fn, k, v)
            i += 1
        inspect.signature(fn).bind(**kwargs)
        out = fn(**kwargs)
    except (TypeError, ValueError, OSError) as e:
        out = {"error": f"bad arguments for {name}: {e}"}
    print(json.dumps(out, ensure_ascii=False, default=str, allow_nan=False))
    return 1 if isinstance(out, dict) and out.get("error") else 0


if __name__ == "__main__":
    sys.exit(main())
