# Decision: ^NSEI (NIFTY 50), NSE, horizon 2w, as of 2026-09-27

**Direction: UP**, confidence low
**Rating: HOLD**
Probabilities up / down / flat: 0.446 / 0.346 / 0.208 (quant prior 0.526 / 0.296 / 0.178)
Expected 80% range: 22,640 to 24,140 INR

The UP label comes from the rule (p_up - p_down = 0.100, which clears the 0.08 threshold). It is not a bullish call. Adjusted p_up of 0.446 is below this symbol's own 10-day up base rate of 0.494, so compared with base rates the view leans slightly down. The range is the quant 80% range (22,790.26 to 23,988.54, centred at 23,389.40) with its half-width widened by 25%. I widened it because the research plan judged the quant range too narrow with the RBI MPC falling inside the horizon.

## Plan
NO TRADE. Size multiplier 0 on the trader's proposal, which is already no trade. There is no position, so there is no entry, stop, target or time stop. The instrument would be NIFTYBEES.NS, since the index itself cannot be traded and SHORT_OK=false.

A conditional setup is recorded here but not authorized. It could become a trade only if a future re-run confirms it:
- Setup: a small mean-reversion long in NIFTYBEES.NS at about 263.3 to 264.1 (index 23,070 to 23,140.5).
- Stop: based on the support level, on an index close below 23,070.15 (proxy about 263.3). The tool's ATR stop at 256.33 is not used.
- Targets: 268.8 (index SMA20 23,553.3), then 273.8 (index SMA50 23,994.46).
- Exit: flatten before the RBI MPC decision (2026-10-05 to 10-07) and within 10 trading days at most.

Capital is 0.0 in settings, so this setup has no size until trade_plan is re-run with the level stop and configured capital (30-trade-proposal.md, 00-request.md).

## Why
- The price model shows no edge. The quant edge over base rate is 0.032, flagged "no tilt" with LOW confidence, on n_effective of only 52.6. The trend factor (-0.143) and reversion factor (+0.079) roughly cancel each other (01-market.md, 20-research-plan.md).
- The forces behind the seven-week slide are still in place and specific to India: WTI +12.38% over 1m, US 10Y +11.15% over 1m, DXY +1.82%, the rupee weaker, and reported FII outflows, while the S&P 500 is +0.88% over 1m. This pushed adjusted p_up below base rate (20-research-plan.md, from 02-fundamentals.md and 03-news.md).
- The RBI MPC decision (2026-10-05 to 10-07) falls inside the horizon and could gap the index either way. The index/ETF proxy cannot defend a stop based on a close against an overnight gap (03-news.md, 40-risk-conservative-r1.md).

## Against
- Bull case, still standing: price sits on support (23,116.10 / 23,070.15) with stochastic at 13.76/17.3 and %B at 0.19. The decline is a low-volume grind, not capitulation: realized vol is at the 27th percentile and volume is 0.82x average. The MACD histogram (-17.56) is rising. Taken together, a relief bounce toward the SMA20 or SMA50 is plausible, and the level-stop version of the long has good reward-to-risk (01-market.md, 40-risk-aggressive-r1.md).
- Bear case, still standing: the downtrend is structural. ADX is 31.99 with -DI 31.89 against +DI 12.51, the 50-day average is below the 200-day (death cross), and price is below all three SMAs. A break below 23,070.15 opens a path to the lower band at 22,876.9 and the 52-week low at 22,331.4 (01-market.md).

## Invalidation
This HOLD is revisited before the 10-day review on either of these:
- An index close below 23,070.15 on above-average volume moves the view toward UNDERWEIGHT.
- An index close above 23,994.46 on above-average volume, or crude rolling back toward the $80s, moves the view toward OVERWEIGHT (20-research-plan.md).

## Risk committee
Aggressive: approve larger / Neutral: wait for trigger / Conservative: approve (no trade) -> I agree with the conservative and neutral seats that probability, not payoff shape, is the constraint. p_up is below base rate, so a favorable R:R rests on a coin flip. The aggressive seat is right that price is already at the top of the trigger zone and that the level stop limits risk tightly. That is why the conditional setup and its level stop are recorded above. It does not justify taking size now: only one seat approved larger, so a multiplier above 1 is ruled out, and no seat made the case for more than zero given no edge and capital not configured. From the conservative seat I take the requirement to flatten before RBI and to enforce the stop manually on a close.

```json
{"symbol": "^NSEI", "name": "NIFTY 50", "exchange": "NSE", "currency": "INR", "as_of": "2026-09-25", "horizon": "2w", "horizon_days": 10,
 "direction": "UP", "confidence": "low", "rating": "HOLD", "p_up": 0.446, "p_down": 0.346, "p_flat": 0.208,
 "quant_prior": {"p_up": 0.526, "p_down": 0.296, "p_flat": 0.178}, "range_80pct": [22640, 24140],
 "action": "NO TRADE", "instrument": "NIFTYBEES.NS", "entry_zone": null, "stop": null, "targets": [],
 "size_multiplier": 0, "invalidation": "Index close below 23070.15 on above-average volume (toward UNDERWEIGHT) or close above 23994.46 on above-average volume (toward OVERWEIGHT)", "review_after_trading_days": 10}
```

Not investment advice. Generated by tradefloor from public data; verify before acting.
