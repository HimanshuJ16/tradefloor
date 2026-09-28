# Contributing

## Setup

From the repo root:

```
python tools/build.py --check                                    # host files match sources
uv run --project server --group dev pytest tests server/tests    # offline, about 2 seconds
uv run --project server python server/scripts/check_markets.py   # live: every registry symbol
uv run --project server python server/scripts/smoke.py           # live: every MCP tool over stdio
claude plugin validate --strict .claude-plugin/plugin.json
```

## One source, many hosts

Never edit a generated file. The sources are:

| Edit | For |
|---|---|
| `rules/tradefloor.md` | the protocol every host's instruction file carries |
| `roles/*.md` | the twenty-three desk roles (frontmatter: `tier` quick or deep, `web` live-only or never, `desk` analyze, scout, swarm or both) |
| `skills/*/SKILL.md` | the six procedures, shared by every host that loads skills |
| `tools/adapters.py` | manifests, MCP launch spec, commands, per-host agent formats |
| `server/pyproject.toml` | the version every manifest carries |

Then run `python tools/build.py`. Skills must stay host-neutral: no `${user_config...}`,
no host-only tool names. Defaults come from the `defaults` field of `resolve_symbol`.
Hosts and their state: [docs/agent-portability.md](docs/agent-portability.md).

## Rules

- **Numbers are computed in code, never by the model.** A new metric goes into
  `indicators.py` or `forecast.py` with a test, and the agents are told to read it.
- **Point in time.** Any new dated data source takes `as_of` and returns nothing after
  it. A source that cannot do that is marked `point_in_time: false`. Add a
  no-look-ahead test in the style of `test_factors_have_no_lookahead`.
- **Fail visibly.** Tools return `{"error": ...}`; they never substitute a default value
  for missing data.
- **Markets.** Adding an exchange means a row in `EXCHANGES` with suffix, currency,
  timezone, benchmark and news locale, a case in `tests/test_markets.py`, and a clean
  `check_markets.py` run. Cite the source of the suffix in the PR.
- **Agent prompts.** Keep the output templates stable; later agents and the journal
  parse them. A prompt change that alters a template changes every downstream role.
- **No order execution.** Broker integrations are out of scope for this repository.

## Adding a data vendor

Put the fetcher in `data.py` behind the same shape as the existing ones, and keep keys
optional (read from environment variables, never required). Document the variable in
`docs/agent-portability.md`.
