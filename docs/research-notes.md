# Research notes: TradingAgents and what tradefloor changes

Read on 2026-09-27. Sources:
- Paper: Xiao, Sun, Luo, Wang, "TradingAgents: Multi-Agents LLM Financial Trading
  Framework", arXiv:2412.20138 (v1 2024-12-28, v7 2025-06-03).
  https://arxiv.org/abs/2412.20138
- Code: https://github.com/TauricResearch/TradingAgents (Apache-2.0), main branch,
  README and `tradingagents/` package as of the date above (release notes list v0.5.1,
  2026-09).

tradefloor contains no TradingAgents code. It reuses the organizational idea (a trading
firm of specialised agents) and re-implements it differently.

## What the paper proposes

A trading firm simulated with LLM agents:

- **Analyst team**: fundamentals, sentiment, news, technical. Each writes a report.
- **Researcher team**: a bull and a bear debate the reports for n rounds; a facilitator
  "reviews the debate history, selects the prevailing perspective, and records it as a
  structured entry".
- **Trader**: turns the research into a transaction proposal.
- **Risk management**: risk-seeking, neutral and conservative agents debate the
  proposal, again with a facilitator.
- **Fund manager**: approves and executes.

Two design choices matter more than the org chart:

1. **Structured communication.** Agents "communicate primarily through structured
   documents" held in a global state; natural language is used "exclusively during
   agent-to-agent conversations and debates". This avoids the telephone effect of long
   chat histories.
2. **Quick versus deep models.** Cheap models (gpt-4o-mini, gpt-4o) for retrieval and
   summarising; a reasoning model (o1-preview) for analysis and decisions.

## What the paper shows, and what it does not

Backtest: 2024-01-01 to 2024-03-29, results reported for AAPL, GOOGL and AMZN against
buy-and-hold, MACD, KDJ+RSI, ZMR and SMA.

| Ticker | TradingAgents CR% | Sharpe | MDD% | Best baseline MDD% |
|---|---|---|---|---|
| AAPL | 26.62 | 8.21 | 0.91 | 1.09 (KDJ) |
| GOOGL | 24.36 | 6.39 | 1.69 | 1.08 (KDJ) |
| AMZN | 23.21 | 5.60 | 2.11 | 0.82 (ZMR) |

The limits of that evidence:

- **Three months, three large-cap US stocks, one regime.** About 60 trading days per
  ticker. A Sharpe ratio of 8.21 estimated from 60 daily returns has a standard error of
  roughly 2 annualized; it cannot distinguish skill from a lucky quarter. The paper
  itself attributes the short window to cost: "11 LLM calls & 20+ tool calls/prediction".
- **Drawdown was not uniformly better.** On GOOGL and AMZN the framework's max drawdown
  was higher than the best rule-based baseline.
- **No probabilities.** The output is a buy/hold/sell decision (a five-tier rating in the
  current code). A rating cannot be scored for calibration, so there is no way to tell a
  lucky confident call from a skilled one.
- **The LLM reads raw indicator tables.** Arithmetic and comparison over numeric tables
  is where language models are least reliable, and nothing checks the numbers an agent
  quotes against the numbers it was given.
- **US-centric data.** SEC EDGAR, StockTwits, FRED. The current code maps regional
  benchmarks, but the data depth outside the US is thin.

The repository has improved on several of these since the paper: point-in-time
integrity across dated paths (v0.5.0), backtesting over ticker/date grids, structured
Pydantic schemas for the research plan, trader proposal and portfolio decision, a
`RATING_REVIEW` sentinel instead of defaulting unparseable output to Hold, and a
reflection step that writes a 2 to 4 sentence lesson after outcomes are known and
re-injects it into later prompts.

## What tradefloor changes

| Area | TradingAgents | tradefloor |
|---|---|---|
| Host | Python app with its own CLI and LLM clients | Plugin for Claude Code; MCP server for any agent host |
| Arithmetic | LLM reads indicator tables | Indicators, forecast, sizing computed in code; agents interpret |
| Output | Rating (5 tiers) and trade proposal | Direction with up/down/flat probabilities, tilt vs base rate, 80% range, rating, sized plan |
| Where the probability comes from | Implicit in the LLM's rating | Frequencies after similar setups in the symbol's own history, shrunk to the base rate by effective sample size |
| LLM judgement | Unbounded | May move the quant prior at most 0.10, with a stated reason |
| Evidence | Reports cite nothing mechanically | Every number cited to the tool that produced it; the research manager strikes claims whose numbers do not match |
| Markets | US depth, regional benchmark map | 41 venue definitions, 37 index, commodity, FX and crypto instruments under 73 accepted names, with tradeable proxies, localized news per exchange, currency and price-unit notes (pence, cents, agorot) |
| Point in time | Fixed across dated paths in v0.5 | `as_of` on every dated tool; current-only sources flagged `point_in_time: false`; web search off in historical runs |
| Learning | Reflection text re-injected into prompts | Journal of every call, scored after the horizon: hit rate, Brier vs base-rate reference, stop hits, quant vs full-desk split |
| Cost | 11 LLM calls per prediction in the paper | Quick mode: zero agents. Standard: 12 agent calls. Deep: 17 |
| Execution | Simulated fund-manager execution | None, by design. Suggestions only; no broker keys |

## Known gaps in tradefloor 0.1

- The factor weights in the setup score are priors, not fitted. That is deliberate (fitting
  per symbol overfits), but it means the score's only job is to define "similar setup";
  if it carries no information for a symbol, the conditional rates collapse to the base
  rate and the output says "no tilt".
- Fundamentals, analyst targets, short interest and option chains from Yahoo are current
  snapshots. Historical runs exclude them, so historical runs are thinner than live ones.
- No full backtest harness yet. The journal scores live calls; a grid backtest over
  `as_of` dates of `direction_forecast` is cheap (no LLM) and is the next piece of work.
- Yahoo Finance is unofficial and rate-limited, and its coverage of small exchanges is
  uneven. `server/scripts/check_markets.py` checks every registry symbol.
