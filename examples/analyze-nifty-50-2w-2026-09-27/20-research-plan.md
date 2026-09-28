# Research plan: ^NSEI, horizon 2w
Winner: neither
Rating: HOLD
Direction: UP
Probabilities: quant prior 0.526/0.296/0.178 -> adjusted 0.446/0.346/0.208
Adjustments:
- up -0.05, down +0.05: the exogenous drivers the price model cannot see are all still moving against NIFTY in the last month (WTI $92.41, +12.38% 1m; US 10Y 5.184, +11.15% 1m; DXY +1.82% 1m; rupee -0.37% 1m; reported FII outflows), and the S&P 500 is +0.88% 1m, so the weakness is India-specific rather than a global dip that fades on its own (02-fundamentals.md, 03-news.md). I kept this at 0.05, not 0.10, because the trend factor (-0.143) already prices in part of this through the 4.41% 1m decline.
- up -0.03, flat +0.03: the RBI MPC meeting on 2026-10-05 to 10-07 is a scheduled event inside HORIZON (03-news.md). Per the event rule, this moves probability toward flat and widens the range. It adds no conviction either way. Treat the quant 80% range of 22,790.26 - 23,988.54 as too narrow.
- No adjustment for the J.P. Morgan $115B inflow thesis. 03-news.md itself calls it "pure narrative until" it shows up in FII data.
- No adjustment for TCS Q2 results (2026-10-08), which fall one day outside HORIZON.
- Net moves: up -0.08, down +0.05, flat +0.03. All are within the 0.10 cap, and the total is 1.000.

Direction check: p_up - p_down = 0.100, which is at least the 0.08 threshold, so the rule gives UP. The margin is thin. Adjusted p_up of 0.446 is below this symbol's own 10-day up base rate of 0.494 (01-market.md). So this UP label reflects the index's normal upward drift, not a bullish signal. Relative to base rates, the adjusted view leans slightly down.

## Struck claims
None struck. I checked every cited number in both debate files against the analyst reports, and all of them match: quant probabilities and base rates, reversion +0.079, RSI 34.23, stoch 13.76/17.3, %B 0.19, MACD hist -17.56, volume 0.82x, vol 27th pct, VIX 12.16 / 46th pct, JPM $115B, ADX 31.99, SMAs, returns, macro levels, RBI dates, 6/1/15 headline split, support 23,116.10 / 23,070.15.

Two characterizations were discounted but not struck, because the numbers are correct and only the reading was stretched:
- Bull calls the quant output "a small but real tilt toward up". 01-market.md says the opposite: "no tilt: in line with this symbol's base rate", with an edge vs base rate of 0.032 that it calls negligible and confidence LOW. Bull's lead point therefore carries far less weight than presented.
- Bull says RSI14 34.23 is "in oversold territory". 01-market.md says RSI is "weak, not yet extreme oversold". Only the stochastic is oversold.
- Bear presents a hawkish RBI hold as a downside catalyst. The repo rate has been 5.25% at a neutral stance since August (03-news.md), so a hold is the status quo, not a surprise. This is an inference, not evidence, and I gave it no directional weight.

## Deciding evidence (the two facts that decided it, with citations)
1. The quant model's edge over this symbol's base rate is 0.032, flagged "no tilt" with LOW confidence and n_effective 52.6. The trend factor (-0.143, bearish) and the reversion factor (+0.079, bullish) roughly cancel (01-market.md). The price model shows no edge in either direction, and that is the main reason neither side wins.
2. The macro drivers behind the seven-week slide are still live and India-specific: WTI +12.38% 1m, US 10Y +11.15% 1m, rupee weakening, and S&P 500 +0.88% 1m above its 200d (02-fundamentals.md, 03-news.md). This justifies trimming the bull's prior, but not flipping it. Most of the bear's technical case (death cross, ADX, price below MAs) is already inside the model's trend factor, so counting it again would double-count.

## What the losing side got right
Neither side won, so this covers both.
- Bull: the model's reversion factor is real. Stochastic 13.76/17.3 and %B 0.19 put price at the lower band. Realized vol at the 27th percentile and volume at 0.82x mean the decline is a grind, not a capitulation. Shorting at 23,140 is shorting directly into support (23,116.10 / 23,070.15).
- Bear: the structural trend is intact (ADX 31.99, -DI 31.89 vs +DI 12.51, 50d below 200d). The drivers have not reversed. Any bounce toward the 50d SMA (23,994.46) is a move against the trend, not a trend change.

## Strategic actions (what the trader should build: direction, holding period, what to avoid)
- No directional conviction trade. The adjusted probabilities give no edge vs base rate, so HOLD means flat or minimal exposure, not a trimmed long dressed up as a view.
- If the trader wants a tactical position, the only defensible one is a small mean-reversion long taken near support (around 23,070-23,140), stop on a close below 23,070.15, first target the SMA20 23,553.3, stretch target 23,994.46. Size it small, because p_up (0.446) is below base rate.
- Holding period: no more than 10 trading days. Cut or halve any position before the RBI MPC on 2026-10-05 to 10-07. Do not hold full size through the decision.
- Avoid: opening a new short at support after seven down weeks with oversold stochastics. Avoid adding longs above the SMA20 while the 50d is below the 200d. Avoid acting on the JPM inflow narrative until FII flow data confirms it.
- Re-rate triggers: a close below 23,070.15 on above-average volume moves the view toward UNDERWEIGHT. A close above 23,994.46 on above-average volume, or crude rolling toward the $80s, moves it toward OVERWEIGHT.
