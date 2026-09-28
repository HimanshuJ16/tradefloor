---
name: swarm
description: Simulate the market crowd around one stock or index - foreign institutions, domestic funds, retail, prop desks, market makers, event funds - reacting to the latest news, with thousands of simulated traders across a thousand Monte Carlo worlds calibrated to the stock's own volatility. Returns the spread of outcomes, the shift the news causes against normal behaviour, which group moves the price, and what-if scenarios ("what if the RBI hikes 25 bp"). The user can then question any group. Use when the user asks how the market will react to news or an event, wants a what-if or scenario, or asks who is buying or selling.
argument-hint: <symbol or index> [horizon 1w|1m|3m] [what-if "<event>"] [as_of YYYY-MM-DD]
license: MIT
---

# tradefloor: market swarm

Arguments: `$ARGUMENTS` (if that shows literally, take the request from the user's message).

You coordinate. The personas decide how each group reacts; the simulation turns reactions
into odds; the reporter reads it. You do not analyse.

## How roles run in this host

Delegate each role to a subagent if your host has them: `tradefloor:<role>` in Claude
Code, `<role>` elsewhere. Launch parallel roles together. If the host has no subagents,
play the role yourself from `references/<role>.md` in this skill's folder, one at a time.

## 1. Parse and resolve
INSTRUMENT, HORIZON (default `defaults.default_horizon`), WHAT_IF (the text after
`what-if`, optional), AS_OF (optional; a past date is a historical run). Call
`resolve_symbol(INSTRUMENT)` and `swarm_roster(symbol)`.

RUN_DIR = `tradefloor-runs/swarm-<symbol, ^ -> idx->/<AS_OF or today>-<HORIZON>`. Write
`RUN_DIR/00-request.md` with the request and the roster.

## 2. Seed
`seed-analyst` with SYMBOL, NAME, EXCHANGE, HORIZON, AS_OF, RUN_DIR, IS_HISTORICAL, WHAT_IF.

## 3. Personas (parallel)
One `crowd-persona` per group in the roster, all launched together. Give each its GROUP
(id, name, description, behaviour from `swarm_roster`), SYMBOL, HORIZON, RUN_DIR.

If WHAT_IF: a second parallel round, each persona told to react to event W1 in the seed as
well, writing `10-persona-<id>-whatif.md`.

## 4. Report
`swarm-reporter` with SYMBOL, NAME, EXCHANGE, CURRENCY, HORIZON, AS_OF, RUN_DIR,
IS_HISTORICAL, WHAT_IF.

## 5. Deliver
Reply, under 30 lines:
1. `SYMBOL (NAME) · horizon · <agents> traders in <groups> groups · <worlds> worlds`
2. The report's table: baseline, with the crowd, quant model, and the what-if if any.
3. Who moved the price, top three groups, one line each with the reason from their file.
4. The Read paragraph, including how the crowd and the quant model agree or disagree.
5. The run folder and journal id; `review` grades it after the horizon.
6. One line offering to question any group: "Ask the FII desk (or any group) why."
7. `Not investment advice. Public data, possibly delayed; verify before acting.`

## Questions afterwards
When the user asks a group something ("why are FIIs selling?", "what would make retail
buy?"), launch `crowd-persona` for that group again with QUESTION set to the user's words
and the same RUN_DIR; it answers in character from the seed and its own reaction file.
Relay the answer. If the answer changes the group's reaction, rerun step 4.

## Rules
- The simulation is the spread of outcomes around the stock's normal behaviour given these
  reactions. Never present it as a prediction of the future.
- Every number in the reply comes from `50-swarm-report.md`.
