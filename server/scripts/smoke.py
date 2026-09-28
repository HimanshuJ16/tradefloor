"""End-to-end check over the real MCP stdio transport, against live data.

    uv run python scripts/smoke.py

Spawns the server the way a host does, lists tools, and calls each one. Uses a temporary
TRADEFLOOR_HOME so the user's journal is untouched. Exit code 1 on any tool error.
"""

import asyncio
import json
import os
import sys
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

CALLS = [
    ("swarm_roster", {"symbol": "^NSEI"}),
    ("swarm_simulate", {"symbol": "RELIANCE.NS", "horizon": "1m", "worlds": 400, "reactions": [{"group": "fii", "sentiment": -0.5, "conviction": 0.6, "persistence_days": 8}]}),
    ("intraday_scan", {"market": "nifty 50", "at": "2026-09-25 10:30", "top": 3}),
    ("intraday_scan", {"market": "dax", "top": 3}),
    ("intraday_scan", {"market": "nifty 50", "at": "2026-09-25 09:00", "top": 3}),
    ("quick_direction", {"query": "nifty 50", "horizon": "1m"}),
    ("quick_direction", {"query": "toyota motor", "horizon": "2w"}),
    ("resolve_symbol", {"query": "nifty 50"}),
    ("resolve_symbol", {"query": "RELIANCE", "default_market": "NSE"}),
    ("resolve_symbol", {"query": "toyota motor"}),
    ("technical_report", {"symbol": "7203.T"}),
    ("direction_forecast", {"symbol": "^NSEI", "horizon": "1m"}),
    ("direction_forecast", {"symbol": "AAPL", "horizon": "1w"}),
    ("direction_forecast", {"symbol": "SAP.DE", "horizon": "3m"}),
    ("direction_forecast", {"symbol": "BTC-USD", "horizon": "1m"}),
    ("direction_forecast", {"symbol": "^GSPC", "horizon": "1m", "as_of": "2024-03-28"}),
    ("fundamentals", {"symbol": "RELIANCE.NS"}),
    ("news", {"symbol_or_query": "RELIANCE.NS", "days": 7, "limit": 5}),
    ("news", {"symbol_or_query": "^GSPC", "as_of": "2024-03-28", "days": 7, "limit": 5}),
    ("sentiment_signals", {"symbol": "AAPL"}),
    ("macro_context", {"symbol": "RELIANCE.NS"}),
    ("trade_plan", {"symbol": "RELIANCE.NS", "direction": "UP", "horizon": "1m", "capital": 500000, "risk_pct": 1}),
    ("scan", {"symbols": ["AAPL", "MSFT", "INFY.NS", "7203.T", "SAP.DE"], "horizon": "1m"}),
    ("journal_record", {"entry": {"symbol": "^GSPC", "as_of": "2024-03-28", "horizon_days": 21, "price": 5254.35, "direction": "UP", "p_up": 0.6, "p_down": 0.25, "base_p_up": 0.55, "source": "smoke"}}),
    ("journal_review", {}),
]


def brief(name: str, out: dict) -> str:
    if "error" in out:
        return "ERROR " + out["error"]
    if name == "resolve_symbol":
        r = out.get("resolved")
        return f"{r['symbol']} {r['exchange']} {r['kind']} {r.get('name')} proxies={r.get('proxies')}" if r else f"candidates={[c['symbol'] for c in out['candidates'][:4]]}"
    if name == "intraday_scan":
        if out["mode"] == "premarket":
            picks = ", ".join(f"{c['symbol']} p_big={c['p_big_move']} lean={c['direction'].get('lean')}" for c in out["candidates"])
            return f"premarket for {out['target_session'][:10]}, {out['universe_size']} stocks | {picks}"
        picks = ", ".join(f"{c['symbol']} {c['direction']} pF={c['probabilities'].get('p_follow')}" for c in out["candidates"])
        return f"{out['mode']} {out['universe_size']} stocks, calib {out['calibration']['samples']} | {picks}"
    if name == "swarm_roster":
        return ", ".join(f"{g['id']} {g['weight']}" for g in out["groups"])
    if name == "swarm_simulate":
        b, sc = out["baseline"], out["scenario"]
        return f"{out['agents']} traders x {out['worlds']} worlds, base up {b['p_up']} -> {sc['p_up']}, top mover {out['who_moved_the_price'][0]['group']} {out['who_moved_the_price'][0]['moved_price_pct']}%"
    if name == "quick_direction":
        i, p = out["instrument"], out["probabilities"]
        return f"{i['symbol']} {out['direction']}/{out['confidence']} up={p['up']} down={p['down']} tilt={out['tilt']['value']} plan={(out.get('plan') or {}).get('side')} journal={out.get('journal_id')} {out.get('note') or ''}"
    if name == "direction_forecast":
        p = out["probabilities"]
        return f"{out['symbol']} as_of={out['as_of']} {out['direction']}/{out['confidence']} tilt={out['tilt']['value']} up={p['up']} down={p['down']} flat={p['flat']} range80={out['expected_range_80pct']['low']}..{out['expected_range_80pct']['high']} n_eff={(out.get('similar_setups') or {}).get('n_effective')}"
    if name == "technical_report":
        return f"{out['symbol']} {out['last_date']} close={out['last_close']} regime={out['regime']} rsi={out['rsi14']} adx={out['adx']} rs3m={out.get('relative_strength_vs_benchmark_pct', {}).get('3m')}"
    if name == "fundamentals":
        return f"{out.get('longName')} pe={out.get('trailingPE')} quarters={len(out.get('quarterly', {}))} next_earnings={out.get('next_earnings')}"
    if name == "news":
        return f"{out['count']} items, latest: {out['items'][0]['published'][:10] + ' ' + out['items'][0]['title'][:70] if out['items'] else '-'}"
    if name == "sentiment_signals":
        return f"reco={out['recommendation_key']} options={out['options']} reddit_posts={out.get('reddit', {}).get('posts_last_week', out.get('reddit'))}"
    if name == "macro_context":
        return ", ".join(f"{k}={v['last']}" for k, v in out.items() if isinstance(v, dict) and "last" in v)
    if name == "trade_plan":
        return f"{out['side']} entry={out.get('entry_zone')} stop={out.get('stop')} targets={out.get('targets')} qty={out.get('sizing', {}).get('quantity')}"
    if name == "scan":
        return " | ".join(f"{r['symbol']} {r['direction']} net={r['net']}" for r in out["ranked"]) + f" errors={out['errors']}"
    if name == "journal_review":
        return json.dumps(out["summary"])
    return json.dumps(out)[:160]


async def main() -> int:
    home = tempfile.mkdtemp(prefix="tradefloor-smoke-")
    params = StdioServerParameters(command=sys.executable, args=["-m", "tradefloor.server"], env={**os.environ, "TRADEFLOOR_HOME": home})
    failures = 0
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            print(f"tools ({len(tools.tools)}): {', '.join(t.name for t in tools.tools)}")
            for name, args in CALLS:
                res = await s.call_tool(name, args)
                text = res.content[0].text if res.content else "{}"
                try:
                    out = json.loads(text)
                except json.JSONDecodeError:
                    out = {"error": text[:200]}
                bad = res.is_error or "error" in out
                failures += bad
                print(f"{'FAIL' if bad else 'ok  '} {name:<18} {brief(name, out)}")
    print(f"\n{len(CALLS) - failures}/{len(CALLS)} calls ok")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
