# Intraday picks: nifty 50, live, scan at 2026-09-22 11:15 IST

Day: selective. Regime: trend down (weak), favoured side short. Breadth is 33.3% above VWAP and the index is -0.26%. Recent momentum shows no edge (43% follow vs 40% fade). India VIX is 11.0, which is low.

| # | Symbol | Side | Trigger | Stop | Targets | Size | p_follow (base) | Why |
|---|---|---|---|---|---|---|---|---|
| 1 | INFY.NS | SHORT | 1019.2 (break of day low) | 1027.4077 (VWAP; 5-min close above) | 1013.9 (partial, daily support) / 1010.9923 / 1002.7846 | 0.5x | 0.456 (0.436) | It is the only candidate where the regime tilt and the daily trend both run with the trade: -DI 33.1 > +DI 19.4, RSI14 35.1, price below all SMAs. Scan edge is +0.069 (Q4). It is half size because the tape is grade B (RVOL 1.42, efficiency 0.43), the calibration is near a coin flip, the feed is delayed 15 minutes, and no quantity has been sized. Take a partial at 1013.9 support and run the rest only if a 5-min close breaks below it. |

Valid: live, until square-off at 15:05 IST, and only if price trades down through 1019.2. The order does not fill at the 1022.7 print.
Data: exchange delay 15 min, data age 0.0 min at scan. Re-check triggers against a live quote before placing.

## Risk committee
Aggressive: approve, full size, no adds / Neutral: approve smaller (T1 is about 1R, and T1 sits below untested support 1013.9) / Conservative: approve smaller, 0.5x cap until the real-time trigger, the 1013.9 scale-out and computed sizing are all in place -> Took INFY.NS SHORT at 0.5x, adding 1013.9 as the first scale-out. Full size is not justified: two of three seats asked for smaller, and the conservative seat's conditions for full size (real-time confirmation and a computed quantity) are not met in the run files. Final quantity = 0.5x of the user's per-trade risk budget / 8.2077 risk per share.

```json
[{"symbol": "INFY.NS", "side": "SHORT", "trigger": 1019.2, "stop": 1027.4077, "targets": [1013.9, 1010.9923, 1002.7846], "size_multiplier": 0.5, "p_follow": 0.456, "base_p_follow": 0.436, "journal_id": "07b6c9341f58"}]
```

Not investment advice. Public data, possibly delayed; verify before acting.
