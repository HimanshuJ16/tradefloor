---
name: review
description: Score tradefloor's past calls against what the market actually did - hit rate, Brier score against the base-rate reference, stop hits, realized returns - and report whether the calls show skill. Use when the user asks how past predictions did, wants a track record, or after a call's horizon has passed.
argument-hint: [symbol]
license: MIT
---

# tradefloor: review the record

Arguments: `$ARGUMENTS`

1. Call `journal_review(symbol)` (symbol optional, from `$ARGUMENTS` if given).
2. Reply with:
   - Summary: scored calls, open calls, hit rate, Brier score for p(up) and the
     base-rate reference Brier, and `beats_base_rate`.
   - A table of scored calls, newest first: date, symbol, horizon, call, p(up),
     realized return, outcome, hit, stop hit.
   - Open calls with bars elapsed out of the horizon.
3. Interpret without spin:
   - Under 30 scored calls, the hit rate is noise. Say that first.
   - Beating the base-rate Brier is the bar. A 60% hit rate on an asset that rose 60% of
     the time is no skill.
   - Separate `quant` from `full` calls if both exist, so the user can see whether the
     agent layer adds anything over the price model.
4. For the three worst misses, read the run folder (`run_dir` in the entry) if it exists
   and name, in one line each, what the desk missed.

If the journal is empty, say so and point to the `direction` and `analyze` procedures,
which record calls automatically. The journal lives in `~/.tradefloor/journal.jsonl` and
is shared by every agent host.
