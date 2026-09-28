# Changelog

## 0.1.0 (unreleased)

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
