---
name: scan
description: Rank a watchlist of stocks, indices, futures or crypto from any mix of exchanges by the quant direction forecast, to find which instruments have the strongest bullish or bearish tilt. Use when the user gives several tickers, asks "which of these", or wants candidates for a full analysis.
argument-hint: <symbols or names, comma or space separated> [horizon] [as_of YYYY-MM-DD]
license: MIT
---

# tradefloor: watchlist scan

Arguments: `$ARGUMENTS`

1. Split the arguments (or the user's message, if `$ARGUMENTS` shows literally) into
   instruments, and pull out HORIZON and optional AS_OF. With no HORIZON, use
   `defaults.default_horizon` from the first `resolve_symbol` result.
2. Resolve each with `resolve_symbol`. Anything that returns candidates rather than a
   single resolution: take the top candidate on the user's home market and mark it `(?)`.
   An index resolves to itself; list its proxies beside it.
3. Call `scan(symbols, horizon, as_of)` once with all resolved symbols (40 at most).
4. Reply with a table sorted by tilt, strongest bullish first:

| # | Symbol | Direction | Conf. | p(up) | p(down) | Tilt | 80% range |

Then:
- Top two bullish and top two bearish tilts, one line each on why (call
  `direction_forecast` for those four only if the table is not enough to say).
- Any symbol with errors, and the error.
- One line: tilt is today's setup versus each symbol's own history; it ranks candidates,
  it is not a buy list. Offer the full `analyze` procedure on the top picks.
- `Not investment advice.`

Index constituent lists are not built in, because they change and stale lists produce
survivorship bias. If the user asks to scan "the Nifty 50" or "the S&P 500", ask for the
symbols or offer to scan the index and its main sector proxies instead.
