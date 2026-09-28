# tradefloor

**A multi-agent trading desk for Claude Code, Codex and Antigravity that quotes odds, not
opinions, and keeps score of every call.**

Analysts research, a bull and a bear argue, a manager judges, a trader plans, a risk
committee pushes back, a portfolio manager decides: the
[TradingAgents](https://github.com/TauricResearch/TradingAgents) design, rebuilt as a
plugin for the coding agent you already use. Three things are different:

1. **The numbers come from code, the odds come from history.** Indicators, probabilities,
   ranges and position sizes are computed in Python. A probability is how often *this*
   instrument actually went up, down or sideways after setups like today's, not a model's
   confidence. The agents may move it by at most 0.10, with a written reason, and every
   figure they use must cite the tool that produced it; a manager agent strikes claims whose
   numbers do not match.
2. **It keeps score.** Every call goes into a journal and is graded once its horizon passes:
   hit rate and Brier score against the base rate for swing calls, R multiples on real
   5-minute bars for intraday calls. You find out whether it has skill instead of being
   told it does.
3. **It works before the open, during the session, and outside the US.** A pre-market scan
   finds the stocks most likely to make a big move today; a live scan finds volume-backed
   momentum; 41 exchanges (NSE, BSE, LSE, Xetra, Tokyo, Hong Kong, Shanghai, ASX, TSX, B3
   and more) with local universes, benchmarks and news. No API keys.

> Not investment advice. Public data, delayed on many exchanges. It never places orders.

![The analyze desk: data tools feed four analysts; a bull and a bear debate; a research manager audits citations and adjusts the quant odds; a trader plans; a risk committee reviews; a portfolio manager decides; the journal grades the call later](assets/analyze-desk.svg)

## What it looks like

![The scout desk: a market universe feeds either the pre-market big-move scan or the live momentum scan; tape, catalyst and regime analysts; an advocate and a skeptic debate; a desk head picks; trader, risk committee and portfolio manager; the journal grades each pick by the close](assets/scout-desk.svg)

`/tradefloor:scout nifty 50`, run on a Sunday for Monday's session: eleven agents
produced this watchlist ([full run](examples/scout-nifty-50-premarket-2026-09-28/)):

```
Day: selective. Regime: range. Continuation after a strong day is 44% (within noise of a
coin flip), and all 8 candidates have lean: null, so the opening-range break picks the side.

KOTAKBANK.NS  either side, 0.5x   p_big_move 0.264 (base 0.234)   typical OR 2.425 (0.6%)
  Board approved the KMIL/KAAML merger on 09-25; moved only -0.71% on 1.47x traded value.
  Skip if it gaps past 407.95 / 399.45 and reverses back in. Square off by 15:05 IST.

Dropped: AXISBANK (no catalyst, fights the daily downtrend), MEESHO (all three risk seats
rejected), PAYTM (its usual opening range is wider than its own skip cap).
```

The same desk, replaying 11:15 IST on 2026-09-22, picked one live trade from 60 stocks:
**INFY short at half size**, because it was the only candidate where the down-trending
day, the daily trend and the calibrated edge agreed. The journal graded it on that session's
real bars: *not triggered*, 0R. ([full run](examples/scout-nifty-50-live-replay-2026-09-22/))

## Measured, not claimed

**Pre-market: can it find today's big movers before the open?** Walk-forward over the last
15 sessions, each day's top 5 chosen using only earlier data, against the rest of the
market ([`eval_premarket.py`](server/scripts/eval_premarket.py)):

| Market | Big move (range ≥ 1.3× normal): picks | Rest | Opening-range trade, avg R: picks / rest |
|---|---|---|---|
| NIFTY 50 | **29%** | 19% | +0.15 (38 trades) / +0.06 |
| S&P 500 | **32%** | 17% | 0.00 (17 trades) / −0.11 |
| DAX | **29%** | 22% | +0.15 (48 trades) / 0.00 |

The big-move lift held in all three markets. The trade column leans the same way on too
few trades to call an edge.

**What it could not find, and says so:**
- Direction before the open. After strong days, the next day continued 44% (NIFTY) to 49%
  (S&P 500, DAX) of the time: a coin flip. The scan shows a side only when the data clears
  two standard errors from 50%, which it usually does not.
- Live momentum follow-through. Over ~53 sessions the strongest live setups followed through
  37% and faded 42% in the NIFTY 50, 35% against 40% in the S&P 500. On such days the desk
  stands aside; in the replay above it took one trade out of sixty stocks.
- Overnight news. Across 1,127 NSE opening gaps, gaps with a company filing overnight
  continued 51% of the time after the open, 58% for big ones (n=62, not yet significant).

All figures were measured on 2026-09-27 over the preceding ~60 days of Yahoo data; rerun the
scripts to update them.

## Install

Requires [uv](https://docs.astral.sh/uv/). No API keys.

**Claude Code**
```
/plugin marketplace add HimanshuJ16/tradefloor
/plugin install tradefloor@tradefloor
```
It asks for your home market, capital and risk; change them later in `/config`.

**Codex**
```bash
codex plugin marketplace add HimanshuJ16/tradefloor
codex plugin add tradefloor@tradefloor
```

**Antigravity** (from a checkout)
```bash
git clone https://github.com/HimanshuJ16/tradefloor
python tradefloor/tools/install.py antigravity --project /path/to/your/project
```

**Any terminal**
```bash
uv run --project tradefloor/server tradefloor intraday_scan "market=nifty 50"
```

The first run installs the Python dependencies (about a minute).

## Use

```
/tradefloor:scout nifty 50                       # before 9:15: likely big movers; after: live momentum
/tradefloor:scout s&p 500 quick                  # scan only, no agents, ~20 s
/tradefloor:scout nifty 50 at "2026-09-25 09:00" # replay any moment in the last ~55 days
/tradefloor:analyze RELIANCE.NS 1m               # full 12-agent desk on one instrument
/tradefloor:direction nikkei 1w                  # quant only, ~30 s
/tradefloor:scan AAPL MSFT INFY.NS SAP.DE 1m     # rank a watchlist
/tradefloor:review                               # how have the calls done?
```

Or ask in plain words: "which NIFTY stocks could move big today?". Codex uses `@scout`,
`@analyze`. Markets for `scout`: `nifty 50`, `bank nifty`, `s&p 500`, `nasdaq 100`, `dax`,
`ftse 100`, `japan`, `hong kong`, `china`, `korea`, `taiwan`, `asx 200`, `tsx`, `brazil`
and more, or your own comma-separated list. Every command:
[docs/commands.md](docs/commands.md).

## How it works

- **MCP server** (`server/`): 15 tools, all arithmetic, point-in-time on request: prices,
  indicators, the calibrated direction model, intraday and pre-market scans, plans, journal.
- **Twenty roles** (`roles/`) for two desks, `analyze` and `scout`, generated into each
  host's agent format. On Claude Code, analysts and debaters run on Sonnet and judges on your
  session model, mirroring the paper's quick/deep split. Codex plays the roles in sequence.
- **Files, not chat.** Each role writes a report into `tradefloor-runs/...`; later roles
  read the files. Every intermediate step is inspectable.

Details and the maths: [docs/architecture.md](docs/architecture.md). What changed from
TradingAgents and why: [docs/research-notes.md](docs/research-notes.md).

## FAQ

**Does it make money?** Unknown, and the project is built to find out rather than assert
it. The pre-market scan measurably picks bigger movers; no trading edge is established.
Run `/tradefloor:review` after a few weeks of calls.

**Why use LLMs at all if the numbers come from code?** For what code does badly: reading
filings and headlines, weighing a catalyst against a chart, arguing both sides, and
explaining a decision. The model is bounded: it can shift a probability by 0.10, not
invent one.

**Look-ahead bias?** Every dated tool takes `as_of` and returns nothing after it;
calibration labels only days whose outcome was known by then; web search is off in
replays; there are tests for it.

**Data?** Yahoo Finance through yfinance (unofficial, for personal research; mind Yahoo's
terms), Google News RSS, public filings. Intraday data is delayed 15 minutes for NSE and
more on some exchanges; every scan reports the delay.

**What does a run cost?** A full desk is 11 to 12 subagent calls and took 9 to 12 minutes in
testing; `quick`, `direction` and `scan` use no agents.

## Limits

- Delayed, unofficial data; no pre-open prices or overnight gaps for most exchanges; no
  exchange holiday calendar.
- Current-only fundamentals, short interest and options are excluded from historical runs.
- LLM output varies between runs; the quant layer does not.
- Hosts follow procedures to different degrees: Antigravity answered with correct numbers
  but skipped the journal step in testing ([details](docs/agent-portability.md)).

## Contributing

```
python tools/build.py --check                                    # generated files in sync
uv run --project server --group dev pytest -q tests server/tests  # 98 offline tests
uv run --project server python server/scripts/smoke.py            # live, every tool over MCP
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [roadmap](ROADMAP.md).

## Citation

The multi-agent design comes from Xiao, Sun, Luo and Wang,
[TradingAgents](https://arxiv.org/abs/2412.20138) (2024). No code is shared.

```
@article{xiao2024tradingagents,
  title   = {TradingAgents: Multi-Agents LLM Financial Trading Framework},
  author  = {Xiao, Yijia and Sun, Edward and Luo, Di and Wang, Wei},
  journal = {arXiv preprint arXiv:2412.20138},
  year    = {2024}
}
```

MIT licensed. See [LICENSE](LICENSE).
