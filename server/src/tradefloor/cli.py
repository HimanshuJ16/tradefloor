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
    "journal_record": server.journal_record,
    "journal_review": server.journal_review,
    "settings": server.settings_tool,
}


def _cast(fn, name: str, raw: str):
    hint = typing.get_type_hints(fn).get(name, str)
    if typing.get_origin(hint) in (typing.Union, types.UnionType):  # Optional[X] / X | None
        hint = next(a for a in typing.get_args(hint) if a is not type(None))
    kind = typing.get_origin(hint) or hint
    if kind is list:
        return [s.strip() for s in raw.split(",") if s.strip()]
    if kind is bool:
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
    while i < len(rest):
        tok = rest[i]
        if tok == "--json" and i + 1 < len(rest):
            kwargs.update(json.loads(rest[i + 1]))
            i += 2
            continue
        if "=" not in tok:
            print(json.dumps({"error": f"expected key=value, got {tok!r}"}))
            return 1
        k, v = tok.split("=", 1)
        kwargs[k] = _cast(fn, k, v)
        i += 1
    try:
        out = fn(**kwargs)
    except TypeError as e:
        out = {"error": f"bad arguments for {name}: {e}"}
    print(json.dumps(out, ensure_ascii=False, default=str))
    return 1 if isinstance(out, dict) and "error" in out else 0


if __name__ == "__main__":
    sys.exit(main())
