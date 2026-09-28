# With tradefloor

Same prompt, same machine, run at the same time, with `--plugin-dir tradefloor`. 32 seconds. The server ran in its own uv environment (`UV_PROJECT_ENVIRONMENT`) because another open session held the checkout's; it does not change the output. Reply verbatim; the call it logged is journal id `5ebfe16f9f24`, scored after 21 trading days.

---

**NIFTY 50: a slight lean up over the next month, but the model's confidence is low.** It's a bet that an oversold market bounces back, while the main trend is still down.

## Direction (1-month horizon, 21 trading days)

| | Up | Down | Flat |
|---|---|---|---|
| Model probability | **57.5%** | 23.3% | 19.3% |
| Usual rate for NIFTY | 53.0% | 27.1% | 20.0% |

- **Price:** 22,837. The model expects it to stay between **22,243 and 24,129** with about 80% likelihood.
- **Why it leans up:** The index is oversold. RSI is 28.5, it's down 5.2% in a month, 2.5% in a week and 13.3% from its 52-week high. The model found 524 similar past setups, which count as only about 25 independent ones. After them, NIFTY rose 61% of the time, with a median gain of 2.6% over the next month. The worst tenth fell about 3% or more, and the best tenth gained 8% or more.
- **Why confidence is low:** Every trend signal is bearish (the price trend, 3-month momentum and 12-month momentum). The index is 10% lower than a year ago. So the lean up comes from past bounces after drops like this, not from strength in the market today. The edge over the usual rate is only about 4.5 points.

## Trade plan (long)

| | Index level | Distance | Reward:risk |
|---|---|---|---|
| Entry zone | 22,735 – 22,837 | at the current price | — |
| **Stop** | **22,207** | −2.8% | — |
| Target 1 | 23,783 | +4.1% | 1.5 |
| Target 2 | 24,129 | +5.7% | 2.05 |
| Target 3 | 24,413 | +6.9% | 2.5 |
| Time stop | If neither the stop nor a target is hit, exit or reassess after 21 trading days | | |

**Key level:** The only support below the price is the **52-week low at 22,331**. The stop sits just under it. If NIFTY closes below 22,331, the bounce idea has failed and the downtrend is continuing, so there's no reason to keep holding. The first resistance is around **24,090**, with more at 24,367–24,379. That's why Target 2 and Target 3 sit where they do.

**How to trade it:** You can't buy the index itself. The tool suggests NIFTYBEES (an ETF that tracks NIFTY) instead:
- Entry zone ₹259.01 – ₹260.95, stop ₹249.04, targets ₹273.60 / ₹278.82 / ₹290.73.
- The ETF plan's stop is further away (−4.6%), so its first target only pays about 1.06× what you risk. I'd use the **index levels above** to decide when to get in and out, and treat the ETF numbers as a rough guide.
- The tool didn't return a position size because no capital or risk % is set in your settings. If you trade NIFTY futures, give me the lot size and your capital and I'll size the position.

**Practical advice:** With low confidence and a falling trend, keep the position small. A more careful approach is to take half now and add the rest only if NIFTY holds above 22,331 on a closing basis over the next few sessions. Leave the stop where it is.

I've logged this call in the journal (ID `5ebfe16f9f24`), so it can be scored against what actually happens after 21 trading days. If you want a fuller view with news, macro and positioning, I can run a full analysis.

*Not investment advice. Public data, possibly delayed; verify before acting.*
