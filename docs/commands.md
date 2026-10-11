# Commands

## Claude Code

```
/tradefloor:scout <market> [long|short] [quick|standard|deep] [premarket|live] [at "YYYY-MM-DD HH:MM"]
/tradefloor:analyze <symbol or index> [horizon 1w|1m|3m|6m|1y] [as_of YYYY-MM-DD] [quick|standard|deep] [short-ok]
/tradefloor:direction <symbol or index> [horizon] [as_of]
/tradefloor:scan <symbols...> [horizon] [as_of]
/tradefloor:review [symbol]
/config                                   # plugin settings: home market, capital, risk, intraday risk, horizon, debate rounds
```

Examples:

```
/tradefloor:scout nifty 50                          # before 9:15: likely big movers; 15+ min in: live momentum
/tradefloor:scout nifty 50 quick                    # scan only, no agents
/tradefloor:scout bank nifty long                   # one side
/tradefloor:scout s&p 500 premarket                 # force the pre-market view
/tradefloor:scout nifty 50 at "2026-09-25 09:00"    # replay a past moment
/tradefloor:scout RELIANCE.NS,TCS.NS,INFY.NS        # your own list
/tradefloor:analyze RELIANCE.NS 1m
/tradefloor:analyze 7203.T 3m deep
/tradefloor:analyze SAP.DE 1m 2024-03-28            # historical, point-in-time
/tradefloor:direction nifty 50 1m
/tradefloor:scan AAPL MSFT INFY.NS HSBA.L 1m
/tradefloor:review KOTAKBANK.NS
```

`scout` markets: `nifty 50`, `bank nifty`, `nifty 500`, `s&p 500`, `nasdaq 100`, `dax`,
`ftse 100`, `japan`, `hong kong`, `china`, `cac 40`, `asx 200`, `tsx`, `korea`, `taiwan`,
`brazil`, `singapore`, `south africa`, `saudi`, `switzerland`, `netherlands`, `spain`,
`italy`, or two or more symbols separated by commas.

Symbols are Yahoo Finance symbols: `.NS` (NSE), `.BO` (BSE), `.L`, `.DE`, `.PA`, `.T`,
`.HK`, `.SS`, `.SZ`, `.KS`, `.TW`, `.SI`, `.AX`, `.TO`, `.SA`, `.JO`, `.SR`; `^` indices,
`=F` futures, `=X` FX, `-USD` crypto; `NSE:TCS` also works; index names like `nifty 50`.

## Codex

The same skills with `@`: `@scout nifty 50`, `@analyze RELIANCE.NS 1m`, `@direction`,
`@scan`, `@review`. Plain questions work in every host.

## Install

```
/plugin marketplace add HimanshuJ16/tradefloor              # Claude Code (or a local path)
/plugin install tradefloor@tradefloor
claude --plugin-dir /path/to/tradefloor                     # Claude Code, one session

codex plugin marketplace add HimanshuJ16/tradefloor         # Codex (or a local path)
codex plugin add tradefloor@tradefloor

python tools/install.py antigravity --project DIR           # Antigravity, or --global
python tools/install.py antigravity --project DIR --dry-run
python tools/install.py antigravity --project DIR --remove
python tools/install.py codex                               # Codex MCP config without the plugin
python tools/install.py --list
```

## Terminal (no AI host)

```
uv run --project server tradefloor list                                   # every tool and argument
uv run --project server tradefloor intraday_scan "market=nifty 50" top=5
uv run --project server tradefloor intraday_scan "market=nifty 50" mode=premarket
uv run --project server tradefloor intraday_scan "market=nifty 50" "at=2026-09-25 09:00"
uv run --project server tradefloor quick_direction "query=nifty 50" horizon=1m
uv run --project server tradefloor scan symbols=AAPL,MSFT,INFY.NS horizon=1m
uv run --project server tradefloor journal_review
uv run --project server tradefloor settings
uv run --project server tradefloor settings key=default_market value=NSE
uv run --project server tradefloor settings key=capital value=500000
uv run --project server tradefloor settings key=intraday_risk_pct value=0.5
```

Settings and the journal live in `~/.tradefloor/` and are shared by every host.

## Development

```
python tools/build.py                                              # regenerate host files
python tools/build.py --check                                      # fail on drift
uv run --project server --group dev pytest -q tests server/tests   # offline tests
uv run --project server python server/scripts/smoke.py             # provider-dependent core MCP canary
uv run --project server python server/scripts/check_markets.py     # live: every market symbol
uv run --project server python server/scripts/eval_premarket.py "nifty 50" "s&p 500" dax
claude plugin validate --strict .claude-plugin/plugin.json
agy plugin validate .
```

## Scenario research tools (0.2.0)

The 0.3 workspace is now the default browser view; the original lab remains at `/lab`.
See [workspace contracts](workspace.md) for the persistent project and research tools.

```bash
uv run --project server tradefloor research_project action=list
uv run --project server tradefloor research_project action=create --file project.json
uv run --project server tradefloor thesis_challenge run_id=YOUR_RUN_ID budget=40
uv run --project server tradefloor research_priority run_id=YOUR_RUN_ID
uv run --project server tradefloor forecast_arena run_id=YOUR_RUN_ID
uv run --project server tradefloor robust_evaluation --file evaluation.json
uv run --project server tradefloor archival_fetch provider=sec identifier=320193
uv run --project server tradefloor information_timeline cutoff=2026-09-28T23:59:59Z
```

Use `tradefloor list` for all 54 tools and exact signatures. Structured file arguments
are one JSON object, for example `{"action":"create","body":{"title":"Earnings thesis"}}`.
SEC requires a contact User-Agent in the server environment; ALFRED requires a FRED key.
External engine integration status is explicit in [extensions.md](extensions.md).

```bash
uv run --project server tradefloor-demo
uv run --project server tradefloor-demo --export dist/demo/index.html
uv run --project server tradefloor scenario_lab case=earnings worlds=300
uv run --project server tradefloor scenario_fork run_id=ID --file fork.json
uv run --project server tradefloor run_bundle run_id=ID
uv run --project server tradefloor run_replay run_id=ID
uv run --project server tradefloor market_sandbox liquidity=0.2
uv run --project server tradefloor experiment_capture symbol=AAPL horizon=1w
uv run --project server tradefloor experiment_mature
uv run --project server tradefloor experiment_scoreboard
uv run --project server tradefloor journal_export
```

`lab` is also a host-neutral skill. `tradefloor list` shows every current signature.
Structured arguments support `--file` and `--json`. See [research-lab.md](research-lab.md)
for event contracts, evidence, sizing, learning review and importing custom snapshots.
Historical bar truncation does not establish historical source/universe availability.
