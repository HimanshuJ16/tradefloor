# Examples

Unedited run folders from real runs in Claude Code, with local paths removed. Each file
was written by one role; later roles read the earlier files.

| Folder | Command | What happened |
|---|---|---|
| [`scout-nifty-50-premarket-2026-09-28`](scout-nifty-50-premarket-2026-09-28/) | `/tradefloor:scout nifty 50` on Sunday 2026-09-27 | Pre-market watchlist for Monday: KOTAKBANK either side at half size; three candidates dropped by the risk committee. 11 roles, 11m32s. |
| [`scout-nifty-50-live-replay-2026-09-22`](scout-nifty-50-live-replay-2026-09-22/) | `/tradefloor:scout nifty 50 at "2026-09-22 11:15"` | Live replay: INFY short at half size from 60 stocks; graded later as not triggered (0R). 11 roles, 9m44s. |
| [`analyze-nifty-50-2w-2026-09-27`](analyze-nifty-50-2w-2026-09-27/) | `/tradefloor:analyze nifty 50 2w` | HOLD, no trade: no edge over two weeks with an RBI decision inside the window. 12 roles. |
| [`before-after-2026-09-28`](before-after-2026-09-28/) | The same question with and without the plugin | Both replies verbatim; used in the README's before/after. |

Read in order: `00-*` (request and data), `01-04` (analysts), `10/11` (debate), `20`
(manager), `30` (trader), `40` (risk seats), `50` (decision).

The pre-market desk above cut its watchlist to one stock by applying a live-trading rule
for range days; the desk-head role has since been changed so pre-market watchlists keep up
to five names at half size on range days.
