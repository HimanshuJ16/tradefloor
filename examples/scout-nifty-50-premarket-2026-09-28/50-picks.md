# Intraday picks: nifty 50, premarket, scan at 2026-09-27 16:31 IST

Day: selective. Regime: range. Favoured side: none. Continuation after a strong day is 44% (within noise of a coin flip), and all 8 candidates have `lean: null`, so the opening-range break picks the side for each stock [03-regime.md][00-scan.json].

| Symbol | Side (either / lean) | p_big_move (base) | Typical OR | Reference levels | Why |
|---|---|---|---|---|---|
| KOTAKBANK.NS | either, 0.5x size | 0.264 (0.234) | 2.425 (0.6%), skip if OR > 3.105 | prev high 407.95 / low 399.45 / close 404.0; resistance 410.29 | Only name that clears the range-day bar of tape grade A plus a fresh catalyst: the board approved the KMIL/KAAML merger on 09-25 and the stock moved only -0.71% on 1.47x traded value. Stops and targets are clean, with 410.29 beyond the 2x-OR target. Half size because the regime is range and the conservative seat flagged gap risk on a live news name. Skip if it gaps past 407.95 / 399.45 and reverses back in. |

Dropped:
- AXISBANK.NS: neutral and conservative both rejected it. There is no catalyst, the upside fights the daily downtrend, and support at 1221.16 sits inside the typical OR.
- MEESHO.NS: all three seats rejected it. The -5.26% drop has no known cause and the 2x-OR long target runs through resistance at 223.1.
- PAYTM.NS: not two rejections (conservative reject, neutral wait), but dropped anyway. Its typical OR of 33.1 is above its own 29.17 skip cap, so on a normal day it does not fire. Its tape grade is C, which fails the desk's range-day bar. The size of the catalyst does not match the scan (a reported 7% drop against 4.4% in the data).

Valid: the target session (2026-09-28, exchange holidays not checked), after the first 15 minutes. Square off by 15:05 IST.
Data: NSE 15-minute delay. Priced off the 2026-09-25 close with no pre-open or gap data, about 2.5 days old at the open. Re-check triggers against a live quote before placing. Set quantity and loss-at-stop from the actual opening range.

## Risk committee
Aggressive: KOTAK approve larger, AXIS approve, PAYTM approve (conditional), MEESHO reject / Neutral: KOTAK approve, AXIS reject, PAYTM wait for trigger, MEESHO reject / Conservative: KOTAK approve smaller (0.5x), AXIS reject, PAYTM reject, MEESHO reject -> took KOTAKBANK.NS only, either side, at 0.5x.

```json
[{"symbol": "KOTAKBANK.NS", "side": "EITHER", "trigger": null, "stop": null, "targets": [], "size_multiplier": 0.5, "p_big_move": 0.264, "base_p_big_move": 0.234, "adr_pct": 0.0154, "prev_close": 404.0, "target_session": "2026-09-28", "journal_id": "e387616b9b25"}]
```

Not investment advice. Public data, possibly delayed; verify before acting.
