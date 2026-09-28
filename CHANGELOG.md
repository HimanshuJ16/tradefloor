# Changelog

## 0.1.1 (2026-09-28)

Added
- Market swarm, `/tradefloor:swarm`. A seed analyst gathers the events; one persona agent
  per market participant group (India: foreign institutions, domestic funds, retail, prop
  desks, market makers, event funds; the US has its own roster) states its reaction as
  numbers; an agent-based simulation runs 2,000 traders over 1,000 Monte Carlo worlds,
  calibrated to the stock's own volatility, tails and drift, and reports the odds against
  normal behaviour, a fan of outcomes and who moved the price. `what-if "<event>"` reruns the
  personas with an injected event; afterwards any group can be questioned in character.
  Calls are journaled as source `swarm`. Inspired by MiroFish; no code shared.
- Two MCP tools, `swarm_roster` and `swarm_simulate`, also in the CLI (17 tools in all).
- `journal_review` breaks scores down by source (quant, full desk, swarm) when there is
  more than one.
- `server/scripts/eval_swarm.py` and the first calibration writeup,
  `benchmarks/results/2026-09-28-swarm-calibration.md`.

Changed
- The quant model's 80% range now uses max(EWMA, 1-year realised) volatility instead of
  the EWMA alone. On one-month outcomes of NIFTY 50 and S&P 500 stocks over the past year,
  its 80% ranges held 73% and 70% of outcomes before and 80% and 77% after.
  `direction`, `analyze` and `trade_plan` ranges are wider as a result.

## 0.1.0 (2026-09-28)

First public version.

- MCP server with 15 tools: symbol resolution for 41 exchanges and index names, technical
  report, calibrated direction forecast, fundamentals, localized news, sentiment signals,
  macro context, trade plan, watchlist scan, intraday scan (pre-market and live), journal
  record and review, settings. Also available as the `tradefloor` CLI.
- Two desks as agents: `analyze` (12 roles for one instrument) and `scout` (11 roles for a
  market, pre-market or live), with every role writing a file the next one reads.
- Journal grading: hit rate and Brier score against the base rate for swing calls; R
  multiples on 5-minute bars for intraday calls; big-move Brier score and a two-sided
  opening-range trade for pre-market picks.
- Point-in-time `as_of` and `at` replays, with no-look-ahead tests.
- Hosts: Claude Code, Codex, Antigravity; generated from one source by `tools/build.py`.
- Walk-forward evaluation script for the pre-market model.
- The MCP server starts with `python -m tradefloor.server`, so a running session on
  Windows cannot block a reinstall by locking a console-script executable.
