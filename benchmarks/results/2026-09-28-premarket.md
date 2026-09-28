# Pre-market scan, walk-forward, 2026-09-28

**Question.** Before the open, can the scan pick stocks that make a big move that session,
more often than the rest of the market does?

**Method.** For each of the last 15 completed sessions per market, the pre-market model
sees only the sessions before it, scores every liquid stock in the universe, and keeps the
top 5. Each stock is then graded on that session's real 5-minute bars:

- **Big move:** the session's high-low range is at least 1.3 times the stock's 20-session
  average range.
- **Trend day:** open-to-close move of at least half the average range, and at least 60% of
  the day's range.
- **Opening-range trade:** a two-sided 15-minute opening-range breakout, stop at the other
  side, target twice the range, exit at the close otherwise; skipped when the range is wider
  than half the average range. Result in R.

A session dated today in the exchange's timezone is never a target, since it may still be
open. Universes are the markets' most-traded home shares from Yahoo's screener.

**Command.**

```
cd server
uv run python scripts/eval_premarket.py "nifty 50" "s&p 500" dax --json ../benchmarks/results/2026-09-28-premarket.json
python ../benchmarks/charts.py ../benchmarks/results/2026-09-28-premarket.json
```

**Result** ([raw](2026-09-28-premarket.json)), sessions 2026-09-04 to 2026-09-25:

| Market | Big move: top 5 picks | Big move: rest | Trend day: picks / rest | Opening-range trade avg R: picks / rest |
|---|--:|--:|--:|--:|
| NIFTY 50 | 22 / 75 (29%) | 103 / 540 (19%) | 33% / 32% | +0.19 (38 trades) / +0.06 (346) |
| S&P 500 | 24 / 75 (32%) | 161 / 960 (17%) | 31% / 28% | 0.00 (17) / −0.11 (431) |
| DAX | 22 / 75 (29%) | 122 / 555 (22%) | 31% / 27% | +0.15 (48) / 0.00 (414) |

**Reading.** The picks made big moves 1.3 to 1.9 times as often as the rest, in all three
markets. They were barely more likely to be clean trend days. The opening-range column
leans the same way, on 17 to 48 trades per market: too few to call an edge.

**Limits.** 15 sessions per market, one period (September 2026), 75 picks per market.
Yahoo's 5-minute bars, which can be revised and are delayed live. The universe is today's
most-traded list applied to past sessions, so it carries some survivorship. No costs or
slippage in the opening-range column. The model's settings (1.3x, top 5, decile buckets)
were chosen before this run and not tuned on it; the analysis that motivated them used the
same ~60-day window, so this is not a clean out-of-sample test. Rerun it on later data.
