---
name: direction
description: Fast, low-cost expected direction for a stock, index, future, FX pair or crypto asset on any exchange - probabilities of up / down / sideways over a horizon, the expected 80% range and a trade plan - from the deterministic quant model only, with no agent debate. Use for a quick read, for many instruments, or when the user asks "which way is X going" without wanting a full analysis.
argument-hint: <symbol or index name> [horizon e.g. 1w|1m|3m] [as_of YYYY-MM-DD]
license: MIT
---

# tradefloor: quick direction

Arguments: `$ARGUMENTS` (if that shows literally, take the request from the user's message).

1. Parse INSTRUMENT, optional HORIZON (`1w`, `2w`, `1m`, `3m`, `6m`, `1y`) and optional
   AS_OF (`YYYY-MM-DD`).
2. Call `quick_direction(query=INSTRUMENT, horizon=HORIZON, as_of=AS_OF)`. It resolves the
   instrument, forecasts, adds technicals and a plan, and records the call in the journal.
   If it returns `note` about a search match, say which listing it picked.

Reply in this shape, under 20 lines:

```
SYMBOL (name) · exchange · currency · as of DATE · horizon H
Direction: UP | DOWN | SIDEWAYS  (confidence C)
  p(up) 0.00 · p(down) 0.00 · p(flat) 0.00   base rate up 0.00 · tilt: <label>
  based on N similar setups (n_eff E) in this instrument's history
Expected 80% range: LOW - HIGH
Trend: <regime, trend strength>  Momentum: <RSI, 1m return>  vs benchmark 3m: <x%>
Drivers: <the three drivers>   <setup_vs_outcome, if present>
Plan: <entry zone, stop, targets, size> | no directional trade | index: levels only, trade via <proxy>
Levels: support <s1, s2> · resistance <r1, r2>
Journal: <journal_id>
```

Then one line on what the quant model does not see (earnings, news, macro) and that the
`analyze` procedure runs the full desk for that. End with the `disclaimer` field.

Every number comes from the tool output. If `read` says there is no measurable edge,
say so plainly rather than implying one.
