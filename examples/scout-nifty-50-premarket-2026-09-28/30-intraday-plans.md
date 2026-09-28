# Intraday orders: nifty 50, scan at 2026-09-27 16:31 IST
Data: 15 min exchange delay [intraday_scan]. Age: n/a — premarket scan priced off the 2026-09-25 close, no live tape yet [tape]. Square off by 15:05 IST [intraday_scan].

No trade is priced yet. Regime is range with no favoured side, so per the range-day rule only KOTAKBANK.NS is eligible to actually fire (grade A + fresh catalyst) [shortlist]; the other three are watch-only. All four use the same two-sided opening-range rule: wait for the first 15 minutes, then trade the break with volume. Sizes and rupee stop-loss cannot be set until the real opening range prints — recompute qty and loss-at-stop from the actual range and the account's risk-per-trade setting.

| Symbol | Side | Trigger | Stop | Target 1 | Target 2 | Qty | Loss at stop | Invalidation |
|---|---|---|---|---|---|---|---|---|
| KOTAKBANK.NS | Either | OR high (long) / OR low (short) | OR low (long) / OR high (short) | 1x OR from trigger | 2x OR from trigger | recompute from actual OR | recompute from actual OR | Skip if OR > 3.105 pts, or gaps past 407.95/399.45 and reverses back in [intraday_scan] |
| AXISBANK.NS | Either (watch only) | OR high / OR low | OR low / OR high | 1x OR from trigger | 2x OR from trigger | recompute from actual OR | recompute from actual OR | Skip if OR > 10.37 pts, or gaps past 1224.5/1191.7 and reverses back in [intraday_scan] |
| PAYTM.NS | Either (watch only, conditional) | OR high / OR low | OR low / OR high | 1x OR from trigger | 2x OR from trigger | recompute from actual OR | recompute from actual OR | Trade only if OR ≤ 29.17 pts; skip if wider, or if gaps past 1747/1658.8 and reverses back in [intraday_scan] |
| MEESHO.NS | Either (watch only) | OR high / OR low | OR low / OR high | 1x OR from trigger | 2x OR from trigger | recompute from actual OR | recompute from actual OR | Skip if OR > 4.196 pts, or gaps past 229.11/216.2 and reverses back in [intraday_scan] |

## Checks
- KOTAKBANK.NS: ok. Resistance at 410.29 is 6.29 pts from last close, beyond 2x the typical OR (4.85 pts), so both mechanical targets sit inside the level with room; typical OR (2.425) is well under the skip cap (3.105) [tape].
- AXISBANK.NS: problem. Support at 1221.16 is only 1.2 pts below last close (1222.4), well inside the typical opening range itself (6.85 pts) [tape]. A mechanical 2x-OR downside target would run straight through that support rather than react to it, and the OR low (short trigger/long stop) may print below the level before the trade even starts. Alternative: use 1221.16 as the short-side target instead of 2x OR, and treat a print below it as part of the gap-and-reverse skip condition, not a normal trigger.
- PAYTM.NS: problem. Typical opening range (33.1 pts) already exceeds the plan's own skip cap (29.17 pts) [tape], so on a typical day this setup should be skipped before any breakout forms. Alternative: only act if the live OR prints at or under 29.17; otherwise stand aside regardless of catalyst.
- MEESHO.NS: problem. Resistance at 223.1 is 6.04 pts from last close, which falls between the 1x-OR (3.65) and 2x-OR (7.3) target distances [tape]. A mechanical 2x-OR long target would push through that resistance rather than respect it. Alternative: use 223.1 as target 2 for the long side instead of the mechanical 2x-OR level; the short side (toward support 206.75, 10.31 pts away) is unaffected.

Not investment advice. Public data, possibly delayed; verify triggers against a live quote once the opening range is set.
