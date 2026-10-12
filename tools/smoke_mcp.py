"""Exercise the real packaged stdio MCP protocol with synthetic sources and no provider calls."""
import argparse
import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def verify(wheel):
    with tempfile.TemporaryDirectory(prefix="tradefloor-mcp-") as home:
        parameters = StdioServerParameters(command=shutil.which("uv") or "uv", args=["run", "--isolated", "--no-project", "--with", str(Path(wheel).resolve()), "tradefloor-mcp"], env={**os.environ, "TRADEFLOOR_HOME": home})
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=30) as session:
                await session.initialize()
                print("MCP initialized", flush=True)
                listed = await session.list_tools()
                names = {tool.name for tool in listed.tools}
                print("Listed tools: " + str(len(names)), flush=True)
                assert {"research_library", "source_discovery", "research_report", "research_session", "scenario_lab"} <= names

                async def call(name, args):
                    print("Calling " + name, flush=True)
                    response = await session.call_tool(name, args)
                    payload = response.model_dump(by_alias=True)
                    assert not payload.get("isError", payload.get("is_error", False)), name
                    value = payload.get("structuredContent", payload.get("structured_content")) or json.loads(response.content[0].text)
                    assert not value.get("error"), value.get("error")
                    return value

                scenario = await call("scenario_lab", {"worlds": 100})
                identifier = scenario["run"]["run_id"]
                doc = await call("research_library", {"action": "import", "body": {"title": "Synthetic MCP source", "source": "Generated fixture", "rights": "MIT synthetic text", "content": "FICTIONAL: cash flow depends on inventory spending.", "published_at": "2026-09-27T00:00:00Z", "available_at": "2026-09-27T00:00:00Z"}})
                hits = await call("research_library", {"action": "search", "body": {"query": "cash inventory"}})
                assert hits["hits"]
                child = await call("research_library", {"action": "freeze", "body": {"run_id": identifier, "selections": [{"document_id": doc["id"], "chunk_id": doc["chunks"][0]["id"]}]}})
                result = await call("research_report", {"run_id": child["result"]["run"]["run_id"]})
                assert "Source appendix" in result["html"] and "inventory spending" in result["markdown"]
                assert "demo_settlement" not in json.dumps(result)
                print(json.dumps({"packaged_mcp": "passed", "tools": len(names), "workflow": "scenario -> document -> search -> evidence branch -> cited report", "provider_calls": 0}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel")
    asyncio.run(verify(parser.parse_args().wheel))
