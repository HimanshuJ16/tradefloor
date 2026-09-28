# Technical report: ^NSEI (NIFTY 50) as of 2026-09-27, horizon 2w
Stance: bearish    Confidence: low

## Evidence
- Regime is downtrend, trend strength "trending", ADX 31.99 with -DI 31.89 dominant over +DI 12.51 [technical_report]
- Price 23,140.5 sits below all three moving averages: SMA20 23,553.3, SMA50 23,994.46, SMA200 24,423.17; 50-day SMA is below the 200-day (death cross) and its 1-month slope is -0.88% [technical_report]
- Returns are negative on most windows: -0.88% 1w, -4.41% 1m, -3.36% 3m, -8.64% 1y; only 6m is positive at +2.79% [technical_report]
- RSI14 34.23 (weak, not yet extreme oversold); stochastic %K 13.76 / %D 17.3 is in oversold territory [technical_report]
- MACD line -244.15 below signal -226.58, histogram -17.56 but rising, i.e. bearish momentum is decelerating, not reversing [technical_report]
- Bollinger %B 0.19 — price is near the lower band (lower 22,876.9, upper 24,229.7), band width 5.74% [technical_report]
- Volume is 0.82x the 20-day average with OBV trending down over the past month — the decline is not being met with rising participation [technical_report]
- 12.11% below the 52-week high of 26,328.55; max drawdown over the past year is -15.18% [technical_report]
- Realized 20-day annualized vol is 9.27%, only the 27th percentile of its own history — the tape is calm, not panicked, despite the downtrend [technical_report]
- Nearest support 23,116.10 then 23,070.15; nearest resistance 24,089.80, then 24,367.30 / 24,378.60 [technical_report]
- direction_forecast base rates for this symbol at 10 trading days are up 49.4% / down 31.6% / flat 19.1%; the model's raw probabilities move only slightly to up 52.6% / down 29.6% / flat 17.8% [direction_forecast]
- Relative-strength factor is null (no benchmark data returned) so RS vs a broader index could not be assessed this run [direction_forecast]

## Quant forecast
Direction: UP, but confidence LOW, tilt "no tilt: in line with this symbol's base rate" (tilt value 0.051, edge_vs_base_rate 0.032 — negligible). p_up 0.526 / p_down 0.296 / p_flat 0.178. 80% expected range over 10 trading days: 22,790.26 - 23,988.54. n_effective 52.6 (thin sample). Top drivers: trend -0.143 (bearish, largest weight), reversion +0.079 (bullish — price is stretched enough that mean-reversion up is favored), MACD -0.071 (bearish). [direction_forecast]

## Read
The structural picture is unambiguously bearish for this horizon: NIFTY is in a trending downtrend by ADX, priced below all three moving averages with a confirmed death cross (50 below 200 SMA), and relative strength data is missing. But the quant model does not confirm a continuation trade — its own probabilities barely move off the symbol's historical base rates (edge of just 3.2 points) and it is explicitly flagged "no tilt" and "low confidence." That mismatch matters: RSI at 34, stochastic near 14/17, and price sitting on the lower Bollinger band all describe a market that is short-term oversold within its downtrend, and the model's own "reversion" factor is the second-largest driver, pushing toward a bounce. Low realized volatility (27th percentile) and below-average volume with falling OBV say this is a grind lower on light participation, not a capitulation — which is consistent with either a continuation or a technical bounce, and does not by itself resolve which. Net: the trend is down and intact, but nothing here says the next two weeks will extend it cleanly rather than produce an oversold relief move back toward the 50-day average before the broader downtrend reasserts.

## Levels
Invalidation (of the bearish trend thesis): a close back above the 50-day SMA at 23,994.46 / the 24,089.80 resistance shelf would say the downtrend is repairing.
Confirmation (of continued downtrend): a break below support at 23,070.15 opens a move toward the lower Bollinger band (22,876.9) and eventually the 52-week low (22,331.4).

## What would change this view
- A close back above 23,994.46 (50-day SMA) with volume above the 20-day average, undoing the death cross bias
- RSI/stochastic reaching a genuine oversold extreme (sub-25 RSI) with a bullish MACD histogram cross, which would validate the model's reversion factor over its trend factor
- Relative-strength data becoming available and showing NIFTY outperforming its benchmark, which this run could not assess (null factor)
