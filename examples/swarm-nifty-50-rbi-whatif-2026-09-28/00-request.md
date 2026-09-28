# Swarm request

- Request: `nifty 50 1m what-if "the RBI raises the repo rate by 25 basis points on 7 October"`
- SYMBOL: ^NSEI (NIFTY 50), exchange NSE, currency INR, kind index, proxy NIFTYBEES.NS, vol index ^INDIAVIX
- HORIZON: 1m
- AS_OF: 2026-09-28 (today; live run, IS_HISTORICAL = false)
- Last close: 22783.35 (2026-09-28)
- WHAT_IF: the RBI raises the repo rate by 25 basis points on 7 October

## Roster (weights are illustrative defaults, not measured shares)

| id | name | weight | fundamental | trend | news | participation | description |
|---|---|---|---|---|---|---|---|
| fii | Foreign institutional investors | 0.18 | 0.5 | 0.3 | 1.0 | 0.6 | Global funds; move on the dollar, US yields, crude, country allocation and earnings revisions. |
| dii | Domestic mutual funds and insurers | 0.17 | 1.0 | -0.2 | 0.5 | 0.7 | Steady SIP inflows; buy dips in quality, slow to react, valuation-anchored. |
| retail | Retail traders | 0.30 | 0.1 | 0.8 | 1.2 | 0.5 | Momentum and headline driven; crowd into trending names, react fast to news and social media. |
| prop | Proprietary and algorithmic desks | 0.20 | 0.0 | 0.5 | 0.8 | 0.9 | Short horizon; trade intraday momentum and news flow, flat by the close. |
| mm | Market makers and option writers | 0.10 | 0.0 | -0.6 | 0.2 | 0.9 | Provide liquidity, hedge options books, lean against short-term moves. |
| event | Event and special-situation funds | 0.05 | 0.6 | 0.0 | 1.5 | 0.4 | Trade specific catalysts: results, mergers, index changes, regulatory decisions. |

Reaction fields: sentiment (-1..+1), conviction (0..1), persistence_days (0.5..60), fair_value_shift_pct (-50..50).
