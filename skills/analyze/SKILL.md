---
name: analyze
description: Run the full tradefloor desk on one stock, index, ETF, future, FX pair or crypto asset on any exchange - analysts, bull/bear debate, research manager, trader, risk committee, portfolio manager - and return the expected direction with probabilities, a sized trade plan and the reasoning. Use when the user asks where a stock or index is heading, whether to buy or sell it, or for a trade idea on it.
argument-hint: <symbol or index name> [horizon e.g. 1w|1m|3m] [as_of YYYY-MM-DD] [quick|standard|deep] [short-ok]
license: MIT
---

# tradefloor: full desk analysis

Arguments: `$ARGUMENTS` (if that shows literally, take the request from the user's message).

You are the desk coordinator. You do not analyse; you route work to the roles, keep the
run folder in order, and deliver the portfolio manager's decision. Every role writes a
file and later roles read those files: the run folder is the shared state.

## How roles run in this host

Delegate each role to a subagent if your host has them. The subagent's name is
`tradefloor:<role>` in Claude Code and Devin, `tradefloor-<role>` in OpenCode, and
`<role>` in Gemini CLI, Copilot CLI and Cursor. Launch the roles marked parallel together
when the host allows it.

If the host has no subagents, or the named one is not available, play the role yourself:
read `references/<role>.md` in this skill's folder, follow it exactly, write its file,
then continue. Finish one role completely before starting the next, and when playing a
role use only what that role is allowed to read. A bull that has already seen the bear's
case is a worse bull.

Every role receives the same header of facts: SYMBOL, NAME, EXCHANGE, CURRENCY, KIND,
AS_OF, HORIZON, HORIZON_DAYS, RUN_DIR, IS_HISTORICAL, PROXIES, and the price unit note
if any.

## 1. Parse the request
- INSTRUMENT: anything that is not one of the tokens below. A ticker (`RELIANCE`,
  `7203.T`, `NSE:TCS`), a company name, or an index name (`nifty 50`, `s&p 500`, `dax`).
- HORIZON: `1w`, `2w`, `1m`, `3m`, `6m`, `1y`. Default: `defaults.default_horizon`.
- AS_OF: a `YYYY-MM-DD` date. Absent means today. A past date is a historical run:
  IS_HISTORICAL=true.
- DEPTH: `quick`, `standard` (default) or `deep`. `quick` runs the `direction`
  procedure instead of the desk.
- SHORT_OK: true if the user wrote `short-ok` or said they can short.

## 2. Resolve
Call `resolve_symbol(INSTRUMENT)`. It returns the resolution and `defaults` (the user's
settings). On `candidates`, pick the match for the user's words and home market; if two
listings are plausible, ask. Then call `direction_forecast(symbol, HORIZON, as_of)` once
to learn HORIZON_DAYS.

RUN_DIR = `tradefloor-runs/<SYMBOL, ^ -> idx-, = -> _>/<AS_OF or today>-<HORIZON>` in the
working directory. Write `RUN_DIR/00-request.md` with the parsed request, the resolution,
DEPTH and ROUNDS (below).

## 3. Analysts (parallel)
`market-analyst`, `fundamentals-analyst`, `news-analyst`, `sentiment-analyst`.
If one fails, retry once; then write its file as "no report: <error>" and continue.

## 4. Debate
ROUNDS = `defaults.debate_rounds` for standard, plus one for deep.
Round 1: `bull-researcher` and `bear-researcher` in parallel, ROUND=1.
Later rounds: both again, each given the other's previous file.
Then `research-manager` with the list of debate files.

## 5. Trader
`trader`, told whether SHORT_OK.

## 6. Risk committee (parallel)
`risk-aggressive`, `risk-neutral`, `risk-conservative`, ROUND=1. Deep runs add a second
round in which each seat reads the other two seats' round-1 files.

## 7. Portfolio manager
`portfolio-manager` with DEPTH. It writes `50-decision.md` and records the call with
`journal_record`.

## 8. Deliver
Reply, under 40 lines:
1. `SYMBOL (NAME) · EXCHANGE · CURRENCY · as of DATE · horizon HORIZON`
2. **Direction**, confidence, up/down/flat probabilities beside the quant prior, and the
   tilt. Low confidence with no tilt: say the evidence shows no edge.
3. **Expected 80% range.**
4. **Rating and plan**: action, entry zone, stop, targets, size, time stop; the proxy for
   an index.
5. **Why** and **Against**, up to three bullets each.
6. **Invalidation.**
7. The run folder and journal id; the `review` procedure scores the call after HORIZON.
8. `Not investment advice. Public data, possibly delayed; verify before acting.`

## Rules
- No analysis of your own between steps. Roles read files, not your summaries of them.
- Every number in the final reply comes from `50-decision.md` or `01-market.md`.
- If resolving or the price history fails, stop and say what failed.
