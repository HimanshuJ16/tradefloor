# Swarm calibration, 2026-09-28

**Question.** Is the market swarm honest about uncertainty? With no news reactions, its
baseline should spread outcomes the way the stock really moves: an 80% range should hold
about 80% of real outcomes.

**Method.** For 14 NIFTY 50 and 13 S&P 500 stocks (the markets' most-traded names), on 12
past dates a month apart (2025-09 to 2026-08), the baseline simulation (1,000 simulated
traders, 400 worlds, no reactions) and the quant model each gave an 80% range for the next
21 trading days, using only data up to that date. The range is scored against the real
21-day return.

**Command.**

```
cd server
uv run python scripts/eval_swarm.py "nifty 50" "s&p 500" --json ../benchmarks/results/2026-09-28-swarm-calibration.json
```

**Result** ([raw](2026-09-28-swarm-calibration.json)):

| | NIFTY 50 (168 cases) | S&P 500 (156 cases) | calibrated |
|---|--:|--:|--:|
| swarm baseline: 80% range held the outcome | 78% | 73% | 80% |
| quant model: 80% range held the outcome | 80% | 77% | 80% |
| outcome below the swarm's 10th percentile | 16% | 13% | 10% |
| average width of the swarm's 80% range | 23.3% | 40.2% | |

**What changed to get here, measured on these same cases.** The first version used the
current (EWMA) volatility and matched only daily volatility; its 80% ranges held 69% and
65% of outcomes, and the quant model's held 73% and 70%. Two changes, both without a tuned
constant: volatility is never assumed lower than the past year's realised volatility, and
the swarm's noise is calibrated to the spread over the whole horizon, because the simulated
market makers and contrarians add mean reversion that narrows it. A multiplier of 1.15 on
volatility scored closer to 80% but was picked by looking at these cases, so it was not used.

**Reading.** The baseline is close to honest on NIFTY stocks and still somewhat
overconfident on the S&P 500 names, whose most-traded list is full of high-volatility
stocks. The misses lean to the downside (16% and 13% below the 10th percentile against 10%):
falls are sharper than rises and the simulated noise is symmetric. Downside skew is on the
roadmap.

**Limits.** One year of monthly dates, overlapping stocks, and today's most-traded list
applied to past dates. This checks the baseline only. Whether the persona reactions add skill
is not measured here; the journal measures it as calls from `/tradefloor:swarm` (source
`swarm`) are scored against the quant model's.
