# Risk: neutral, round 1
Verdict: wait for trigger

## Expectancy in words
No position is live, so there is nothing to price right now — that part of the proposal carries zero expectancy by construction, correctly.

For the conditional setup (the only one the plan defends): entry is proposed right at the support zone (proxy ~263.3-264.1) with the stop placed at the same level (~263.3, on an index close below 23,070.15). That means the stop is very tight relative to the two targets (SMA20 ~268.8, SMA50 ~273.8) — this pays several R if the level holds and loses under 1R, maybe a fraction of 1R, if it doesn't. It is a "small, frequent loss vs large, infrequent win" shape, which is the right shape for a mean-reversion entry taken directly on a support line.

But the win probability behind that shape is thin. The research plan's adjusted p_up (0.446) is barely above p_down (0.346) — a 0.10 margin the plan itself calls thin — and the quant model's edge over this symbol's own base rate is 0.032, flagged "no tilt" and LOW confidence. So the payoff skew is favorable, but the chance of collecting that payoff is close to a coin flip with only a slight lean, not a high-conviction setup. Small size, as the research plan and trade proposal both already say, is the correct match for that combination — a good reward:risk shape riding on a low-conviction direction call.

## Consistency checks (pass / fail each)
- Stop beyond a real level: PASS. The plan explicitly rejects the tool's ATR stop (256.33, equivalent to index ~22,457) because it sits well past the cited support (23,116.10 / 23,070.15) and the lower Bollinger band (22,876.9) — riding roughly 2.7x further than the thesis justifies. It substitutes the level-based stop (close below 23,070.15) instead. This is the correct call: an invalidation stop should sit at the level that disproves the thesis, not at a volatility-derived distance that can sit past it.
- Time stop matches HORIZON: PASS. Time stop is 10 trading days, and HORIZON_DAYS is 10. They match exactly.
- Event inside HORIZON handled: PASS. The RBI MPC meeting (2026-10-05 to 10-07) falls inside the 2-week horizon. The plan already prescribes cutting or halving any position before the decision and caps size at small — this is the correct handling (reduce exposure into a scheduled, direction-agnostic event) rather than ignoring it or holding full size through it.

## Response to other seats (round 1 — n/a)
No other seats' files exist yet this round.

## Correlation note
NIFTYBEES.NS is the tradeable proxy for ^NSEI itself, not a separate instrument whose correlation to a benchmark needs questioning — there is no cleaner index proxy to substitute here, this is already it. 01-market.md flags the relative-strength factor as null (no benchmark data returned), so no read is possible on how this index is behaving versus a broader benchmark; that is a gap in the picture, not a reason to prefer a different instrument.

## Bottom line
The plan as written is internally consistent: no trade now, a specific and defensible conditional trigger, a stop tied to a real level rather than the tool's default, sizing that matches the thin probability margin, and an explicit cut before the in-horizon event. Nothing here needs new numbers or a different instrument. The only action item is procedural, already flagged in 30-trade-proposal.md: if the trigger fires, re-run trade_plan with the level-based stop to get real quantity/risk-in-currency figures before sizing anything.
