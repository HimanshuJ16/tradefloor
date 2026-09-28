# Intraday orders: nifty 50, scan at 2026-09-22 11:15 IST
Data: delay 15 min, age 0.0 min [intraday_scan]. Square off by 15:05 [intraday_scan].

| Symbol | Side | Trigger | Stop | Target 1 | Target 2 | Qty | Loss at stop | Invalidation |
|---|---|---|---|---|---|---|---|---|
| INFY.NS | SHORT | 1019.2 (break of day low) [intraday_scan] | 1027.4077 (VWAP) [intraday_scan] | 1010.9923 [intraday_scan] | 1002.7846 [intraday_scan] | not sized in scan output | risk/share 8.2077 [intraday_scan]; total loss = qty x 8.2077, qty not provided | 5-minute close back above VWAP 1027.4077 [intraday_scan] |

## Checks
- INFY.NS: Stop (VWAP 1027.4077) sits 8.2077 above the trigger, about 40% of the 20.66-point ADR (adr_pct 2.02% on price 1022.7) [intraday_scan] — wider than a single 5-minute bar range, so the stop itself is not the problem. Target 1 (1010.9923) is a different story: it sits below the next daily support at 1013.9, which the tape puts about 42% of ADR from current price, versus target 1's ~57% [01-tape.md, intraday_scan]. That means the plan's first target assumes the trade punches through a support shelf that price has not yet tested. Alternative: treat 1013.9 as the first scale-out level instead of 1010.9923 — take partial profit at or just above that support and only run the balance toward 1010.9923/1002.7846 if the shelf breaks on a 5-minute close.
- Qty/size gap: 00-scan.json's plan block gives risk_per_share (8.2077) but no quantity or capital-based size, and no settings/sizing file exists yet in this run directory. Size must come from the user's capital and intraday risk settings before this can be an executable order — it is not computed here.
- Conditional order: this is a break order, valid only if price trades down through 1019.2; it does not fill on the current 1022.7 print.

File: tradefloor-runs/scout-nifty-50/2026-09-22-1115/30-intraday-plans.md
