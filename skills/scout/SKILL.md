---
name: scout
description: Intraday stock scouting for a market or index - "nifty 50", "bank nifty", "s&p 500", "nasdaq 100", "dax", "ftse 100", "japan", "hong kong" and more countries, or a list of symbols. Before the open it builds a watchlist of stocks likely to make a big move today, with two-sided opening-range plans; during the session it finds stocks with strong live directional momentum. Either way the tradefloor desk (tape, catalyst and regime analysts, advocate versus skeptic, desk head, trader, risk committee, portfolio manager) filters the list. Use when the user asks which stocks to trade intraday, what to watch at the open, or what is moving in a market.
argument-hint: <market or index or country, or symbols> [long|short] [quick|standard|deep] [premarket|live] [at "YYYY-MM-DD HH:MM"]
license: MIT
---

# tradefloor: intraday scout

Arguments: `$ARGUMENTS` (if that shows literally, take the request from the user's message).

You are the desk coordinator for an intraday run. You do not analyse; you route work to
the roles, keep the run folder in order, and deliver the portfolio manager's book. Keep
your own turns short, and launch parallel roles together.

## How roles run in this host

Delegate each role to a subagent if your host has them: `tradefloor:<role>` in Claude
Code, `<role>` elsewhere. Launch the roles marked parallel together. If the host has no
subagents, or the named one is not available, play the role yourself: read
`references/<role>.md` in this skill's folder, follow it exactly, write its file, then
continue.

## Two modes, chosen by the clock

- **premarket** (before the open, when the market is closed, or in the first 15
  minutes): the scan ranks stocks by their chance of a **big move** in the coming session,
  calibrated on this market's recent sessions, because that is what the data can predict
  before the open. Direction before the open is close to a coin flip in the tested
  markets, so a side is shown only when the calibration clears two standard errors;
  otherwise the plan is two-sided and the opening range decides.
- **live** (15 minutes or more into the session): the scan ranks stocks by live
  directional momentum with follow-through probabilities, and plans are trigger-based.

Tell the user which mode ran and why.

## 1. Parse
- MARKET: an index or country name, or two or more symbols separated by commas.
- SIDE: `long`, `short`, or both (default).
- DEPTH: `quick` (scan only, no roles), `standard` (default), or `deep` (two debate rounds).
- MODE: `premarket` or `live` to force one; otherwise automatic.
- AT: `at "YYYY-MM-DD HH:MM"` in exchange time replays a past moment point-in-time
  (within the last ~55 days). A time before the open replays the pre-market view.
  IS_REPLAY = true when given.

## 2. Scan
Call `intraday_scan(market=MARKET, top=8, side=SIDE, at=AT, mode=MODE or "auto")`. If it
returns an error, stop and report it. Note MODE from the result, EXCHANGE, CURRENCY, the
scan time (`as_of`), and SESSION_DATE: `target_session` in premarket mode, `session_date`
in live mode.

RUN_DIR = `tradefloor-runs/scout-<market with spaces as dashes>/<SESSION_DATE>-<premarket or HHMM of as_of>`.
Write the tool's full JSON result to `RUN_DIR/00-scan.json`, and the parsed request to
`RUN_DIR/00-request.md`.

**quick**: stop here. Reply with the table in step 8 built from the scan (no journal
entries: a scan is not a call), the `evidence.read` (premarket) or `regime_read` (live),
and the data delay line.

If the scan has no candidates, say so and stop.

## 3. Analysts (parallel)
`tape-analyst`, `catalyst-analyst`, `regime-analyst`. Give each MARKET, RUN_DIR, MODE,
AT (the scan time), IS_REPLAY.

## 4. Debate
Round 1: `momentum-advocate` and `momentum-skeptic` in parallel, with MODE. Deep: a
second round in which each reads the other's round-1 file. Then `desk-head` with the list
of debate files and MODE.

If the desk head selects nothing, skip to step 7 and let the portfolio manager write an
empty book.

## 5. Trader
`intraday-trader` with MARKET, RUN_DIR, MODE, AT.

## 6. Risk committee (parallel)
`risk-aggressive`, `risk-neutral`, `risk-conservative`, telling each: this is a scout
run in MODE, HORIZON is intraday, the plan files are `20-shortlist.md` and
`30-intraday-plans.md`, and they give one verdict per stock.

## 7. Portfolio manager
`intraday-pm` with MARKET, EXCHANGE, CURRENCY, MODE, AT, SESSION_DATE, RUN_DIR. It writes
`50-picks.md` and records each pick with `journal_record`.

## 8. Deliver
Reply, under 35 lines:
1. `MARKET · EXCHANGE · MODE · scan at <as_of> · for session <SESSION_DATE> · data delay <n> min`
2. One line on what the mode can and cannot tell: premarket predicts the size of the
   move, not its direction, unless a lean is shown.
3. The book as a table. Premarket: symbol, p_big_move against the universe base, side
   (either, or the lean), yesterday's footprint, reference levels, typical opening range.
   Live: symbol, side, trigger, stop, targets, size, p_follow against the base.
   Or "Nothing to trade" with the reason.
4. Two or three candidates that were dropped, one line each on why.
5. What to do next. Premarket: after the first 15 minutes, apply the opening-range rule,
   or rerun this command for the live scan. Live: orders are conditional on the trigger.
6. The run folder and the journal ids; the `review` procedure grades them after the close.
7. `Not investment advice. Public data, possibly delayed; verify before acting.`

## Rules
- No analysis of your own between steps. Roles read files, not your summaries.
- Every number in the reply comes from `00-scan.json` or `50-picks.md`.
- A pre-market pick is never presented as a directional call unless the scan shows a lean.
- A live candidate whose read is "fade tendency" or "no edge" is never presented as momentum.
