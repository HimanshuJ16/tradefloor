"""Real stdio transport smoke without provider calls or user state."""

import asyncio
import json
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from tradefloor import cli


def test_research_tools_through_actual_stdio(tmp_path):
    async def run():
        env = {**os.environ, "TRADEFLOOR_HOME": str(tmp_path)}
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "tradefloor.server"], env=env
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                names = {t.name for t in (await session.list_tools()).tools}
                assert names == set(cli.TOOLS)

                async def call(name, **args):
                    response = await session.call_tool(name, args)
                    assert not response.is_error, response
                    data = json.loads(response.content[0].text)
                    assert "error" not in data, data
                    return data

                await call("settings")
                await call("list_markets")
                await call("swarm_roster", symbol="AAPL")
                desk = await call("run_begin", kind="analyze", request={"symbol": "X"})
                assert desk["workspace"].endswith("reports")
                from pathlib import Path

                (Path(desk["workspace"]) / "50-decision.md").write_text(
                    "Offline transport report", encoding="utf-8"
                )
                await call(
                    "run_finalize", run_id=desk["run_id"], decision={"action": "HOLD"}
                )
                scenario = await call("scenario_lab", worlds=100, sensitivity=False)
                identifier = scenario["run"]["run_id"]
                await call(
                    "scenario_fork", run_id=identifier, overrides={"sentiment": -0.6}
                )
                replay = await call("run_replay", run_id=identifier)
                assert replay["scenario"] == scenario["scenario"]
                bundle = await call("run_bundle", run_id=identifier)
                await call("run_bundle", bundle=bundle)
                p = {"up": 0.6, "down": 0.3, "flat": 0.1}
                await call(
                    "decision_validate",
                    prior=p,
                    adjusted=p,
                    evidence=[],
                    adjustments=[],
                )
                await call(
                    "evidence_audit",
                    evidence=[{"id": "E1", "kind": "assumption", "text": "fictional"}],
                    claims=[{"id": "H", "text": "hypothesis", "evidence_ids": ["E1"]}],
                    cutoff="2026-01-01T00:00:00Z",
                )
                await call(
                    "falsification_check",
                    conditions=[
                        {
                            "id": "F",
                            "metric": "x",
                            "operator": "below",
                            "threshold": 1,
                            "reason": "fails",
                        }
                    ],
                )
                row = {
                    "as_of": "2026-01-01",
                    "probabilities": p,
                    "reference": p,
                    "outcome": "UP",
                    "label_end": "2026-01-02",
                }
                await call("forecast_evaluation", cases=[row])
                await call(
                    "learning_review",
                    training=[row],
                    validation_cases=[{**row, "as_of": "2026-02-01"}],
                )
                await call(
                    "portfolio_stress",
                    holdings=[{"symbol": "X", "value": 100, "currency": "USD"}],
                    shocks={"X": -0.1},
                    account_currency="USD",
                )
                experiment = {
                    "status": "forecast",
                    "source": "test",
                    "symbol": "X",
                    "as_of": scenario["as_of"],
                    "experiment_key": "test",
                    "probabilities": p,
                    "reference": p,
                    "event_contract": scenario["event_contract"],
                }
                saved = await call("experiment_record", experiment=experiment)
                await call(
                    "experiment_settle", identifier=saved["id"], outcome="SIDEWAYS"
                )
                await call("experiment_scoreboard")
                await call(
                    "experiment_mature"
                )  # no unsettled entries, no network calls
                sandbox = await call("market_sandbox", steps=10)
                await call("run_replay", run_id=sandbox["run"]["run_id"])
                await call(
                    "journal_record",
                    entry={
                        "symbol": "X",
                        "as_of": "2026-01-01",
                        "horizon_days": 1,
                        "price": 100,
                        "direction": "UP",
                        "p_up": 0.6,
                        "p_down": 0.3,
                    },
                )
                await call("journal_review", symbol="NONE")
                await call("journal_export")

    asyncio.run(run())
