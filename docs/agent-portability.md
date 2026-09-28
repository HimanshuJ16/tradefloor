# Agent portability

tradefloor ships for three hosts: **Claude Code**, **Codex** and **Antigravity**. Each gets
as much of the three layers as it can carry:

- **Tools**: the MCP server (`server/`), or the same tools as the `tradefloor` CLI.
- **Procedures**: the five skills (`skills/`) and the protocol (`rules/tradefloor.md`,
  generated into `AGENTS.md` and `.agents/rules/`).
- **Desks**: the twenty roles (`roles/`) as the host's own subagents, so analysts, the
  debate and the risk committee run as separate agents.

| Host | Files | What runs | Tested |
|---|---|---|---|
| Claude Code | `.claude-plugin/plugin.json` (inline MCP server, `userConfig`), `.claude-plugin/marketplace.json`, `hosts/claude/agents/` (model split: analysts and debaters on Sonnet, judges on the session model), `skills/` | Both desks as parallel subagents; all five skills as `/tradefloor:<skill>` | `claude plugin validate --strict` passes. `/tradefloor:direction`, `/tradefloor:analyze` (12 agents) and `/tradefloor:scout` (11 agents) ran headless with `claude -p --plugin-dir`. |
| Codex | `.codex-plugin/plugin.json`, `mcp.json` (`${PLUGIN_ROOT}`), `skills/`, `AGENTS.md`; marketplace read from `.claude-plugin/marketplace.json` | Tools and skills; one model plays the roles in turn from `skills/<skill>/references/` | `codex plugin marketplace add` and `codex plugin add` from a checkout installed it, Codex expanded `${PLUGIN_ROOT}`, and the cached server started and served its tools. A model run was blocked by the account's usage limit. |
| Antigravity | `plugin.json` (required at the root), `mcp_config.json`, `agents/` (portable format), `skills/`, `.agents/rules/`; or `tools/install.py antigravity` | Tools, skills, subagents | `agy plugin validate .`: 5 skills, 20 agents, 1 MCP server. Through `install.py antigravity --project`, `agy -p` runs called the tools and answered with correct numbers, but used the individual tools rather than the procedures. |
| Any agent with a shell | the `tradefloor` CLI | Tools | `tradefloor quick_direction`, `settings` and an error case ran live. |

## Where each host finds the server

| File | Root expression | Why |
|---|---|---|
| `.claude-plugin/plugin.json` | `${CLAUDE_PLUGIN_ROOT}` | Claude Code |
| `mcp.json` | `${PLUGIN_ROOT}` | Agent Plugins 1.0, which Codex reads |
| `mcp_config.json` | none: `uvx --from git+...@v<version>#subdirectory=server` | agy 1.1.16 expands no variable in a plugin's MCP config and starts servers in the workspace |
| `tools/install.py` output | absolute path | a local checkout, any project |

The Antigravity plugin route therefore needs the repository public and the release tag
pushed. Until then, `python tools/install.py antigravity` is the working route.

## Settings

The server reads `TRADEFLOOR_*` environment variables, then `~/.tradefloor/config.json`,
then defaults; unexpanded `${...}` placeholders are ignored. Claude Code users set values
in `/config`. Codex and Antigravity users ask the agent, which calls the `settings` tool.
The config file and the journal are shared by all three hosts.

## Adding a host back

The generator made files for fourteen hosts before they were trimmed to these three. To
add one: read the host's current plugin, MCP and agent docs, note which variables it
expands in MCP config, add its files to `targets()` in `tools/adapters.py`, add a test in
`tests/test_tools.py`, install it for real, and record here what ran.
