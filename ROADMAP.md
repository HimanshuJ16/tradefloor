# Roadmap

Ranked by how much each item widens what no other open project in this space offers today:
calibrated odds, a scored track record, pre-market and intraday coverage, and markets
beyond the US.

## Next

1. **Public scored track record.** A scheduled GitHub Action runs `scout` pre-market and
   `direction` on a fixed basket every trading day, commits the journal, and publishes a
   static page: every call, its probability, and its grade. Calibration plots (predicted
   probability against observed frequency) and a quant-versus-desk ablation. The claim
   "it keeps score" becomes a page anyone can audit.
2. **News-driven pre-open desk.** In-news stocks from the last 24 hours (exchange filings,
   Moneycontrol and Economic Times RSS, Google News), classified by agents as catalyst or
   routine, surprise or expected, likely direction. A 9:08 IST pre-open check keeps a call
   only when the auction gap confirms it; the journal measures the agents' reading against
   the 51% (58% for big gaps) baseline measured on NSE filings.
3. **Real-time data adapters, optional and keyed.** Zerodha Kite, Upstox, Dhan and Angel One
   for India; Alpaca and Polygon for the US. Removes the 15-minute delay and adds pre-open
   and pre-market prices. Yahoo stays the zero-key default.
4. **Index options for intraday.** NIFTY and BANKNIFTY option chains: open-interest build-up,
   put-call ratio, max pain, implied volatility and its term structure, as calibrated
   features for the index scan and as plan instruments.
5. **Swarm, next.** Downside skew in the simulated noise (misses fell below the 10th
   percentile 13 to 16% of the time instead of 10%); fit the news-impact scale to how stocks
   actually moved on news days instead of the fixed 0.5 sigma; measured participant weights
   (exchange flow data) in place of the illustrative defaults; an intraday swarm for the
   pre-market desk.

## Then

6. **Agent-layer backtest.** Replay the full desk point-in-time over past sessions to
   measure whether the agents beat the quant prior they start from. Reports the ablation,
   not only returns.
7. **Paper execution.** Place conditional paper orders at the triggers (Alpaca paper, broker
   sandboxes) and track fills, slippage and costs, so the journal grades what a trader would
   actually have gotten.
8. **Transaction costs in every plan.** Brokerage, exchange fees, STT and stamp duty for India,
   SEC fees for the US, and a slippage estimate from the stock's spread and volume.
9. **Scheduling and alerts.** Run the pre-market desk at a set time and push the watchlist to
   Telegram, Slack or a phone notification; alert when a watchlist trigger trades.
10. **Cross-model debate.** Bull and bear on different model families (Claude, GPT through
   Codex, Gemini through Antigravity) so the debate is not one model arguing with itself.

## Later

11. Portfolio mode: analyse holdings together, with correlation and concentration limits.
12. Event calendar: earnings, central bank meetings and index rebalances per market, fed into
    both desks.
13. Exchange holiday calendars, so target sessions are exact.
14. More hosts: the generator already produced files for Gemini CLI, Copilot CLI, Cursor,
    OpenCode, Devin and others before the list was trimmed to the three tested hosts.

Open an issue before starting on any of these; several change the journal format.
