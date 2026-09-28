# Trade proposal: ^NSEI, horizon 2w
Action: NO TRADE (research plan Rating: HOLD; Direction UP carries no edge vs base rate)
Instrument: NIFTYBEES.NS (proxy — ^NSEI index level is not tradeable). SHORT_OK=false, and Direction is UP anyway, so short is moot.

Entry zone: none active. Conditional trigger only — see below.
Stop: n/a (no position)
Targets: n/a (no position)
Reward:risk: n/a
Time stop: n/a
Size: capital not configured — trade_plan(NIFTYBEES.NS, UP, 2w, 2026-09-27) returned entry/stop/target/R:R fields only, no quantity/capital-at-risk fields, so size cannot be stated even if a position were taken.

## Why no trade
20-research-plan.md rates this HOLD: adjusted p_up 0.446 is below the symbol's own 10-day up base rate of 0.494 — "this UP label reflects the index's normal upward drift, not a bullish signal." The quant edge vs base rate is 0.032, flagged "no tilt," LOW confidence, n_effective 52.6 (01-market.md / 20-research-plan.md). Structurally the technical report is bearish (downtrend, ADX 31.99, death cross, price below all three SMAs — 01-market.md), but that is already priced into the trend factor and does not by itself justify a fresh short, which the user cannot take anyway.

## What would trigger a position (per research plan's only defensible setup)
Research plan: "a small mean-reversion long taken near support (around 23,070–23,140 on ^NSEI), stop on a close below 23,070.15, first target SMA20 23,553.3, stretch target SMA50 23,994.46." Size small — p_up is below base rate. Cut or halve before the RBI MPC (2026-10-05 to 10-07); no more than 10 trading days total.

Converting those index levels to NIFTYBEES.NS using the current index/proxy ratio (^NSEI 23,140.5 / NIFTYBEES.NS 264.13 = 0.011413, i.e. proxy ≈ index × 0.011413, from 01-market.md and trade_plan below):
- Entry trigger zone: ~263.3–264.1 (index 23,070–23,140.5)
- Level-based stop: ~263.3 (index close below 23,070.15) — **not** the tool's ATR stop
- Target 1 (SMA20): ~268.8 (index 23,553.3)
- Target 2 (SMA50): ~273.8 (index 23,994.46)

## trade_plan(NIFTYBEES.NS, UP, 2w, 2026-09-27) output, and why it is not used as-is
- entry_zone [262.29, 264.13], stop 256.33 (stop_atr_multiple 2.12, risk_per_unit 7.80), targets [272.53, 275.82, 283.62], reward:risk [1.08, 1.5, 2.5], time_stop 10 trading days.
- The tool's ATR stop (256.33) converts back to an index-equivalent of ~22,457 — well below both cited supports (23,116.10 / 23,070.15), below the lower Bollinger band (22,876.9), and close to the 52-week low (22,331.4). The research plan's own invalidation is a close below 23,070.15 (proxy ~263.3), which is where the mean-reversion thesis is already dead. Riding the ATR stop down to 256.33 means holding roughly 2.7x further past that invalidation point than the thesis justifies — an arbitrary ATR multiple sitting well past the real level, not just beyond it.
- If a position is taken, use the level-based stop (~263.3, confirmed on an index close below 23,070.15) instead of 256.33. Quantity and risk-in-currency must be recomputed by calling trade_plan again with that stop-equivalent setup (or size manually against user-configured capital/risk_pct once available) — not computed here.

## Triggers to enter / to stand aside
- Enter (small size only): ^NSEI trades down into 23,070–23,140 and holds, i.e. NIFTYBEES.NS in the ~263.3–264.1 zone, with the stop at the level-based ~263.3, not the ATR stop.
- Stand aside / do not chase: any long above the SMA20 (23,553.3 / proxy ~268.8) — that is buying above the 50d-below-200d death cross with no confirmation.
- Do not short: this SHORT_OK=false, and Direction is UP (thin margin) — not a short setup regardless.
- Re-rate up (add conviction): a close above 23,994.46 (SMA50, proxy ~273.8) on above-average volume, or crude oil rolling back toward the $80s.
- Re-rate down (avoid entirely): a close below 23,070.15 on above-average volume — take this as confirmation the downtrend is continuing, not a dip to buy.
- Hard deadline: cut or halve any position taken before the RBI MPC decision, 2026-10-05 to 10-07 (03-news.md via 20-research-plan.md).

Not investment advice. Public data, possibly delayed; verify before acting.
