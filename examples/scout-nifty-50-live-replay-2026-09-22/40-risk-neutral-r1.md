# Risk: neutral, round 1
Verdict: INFY.NS SHORT — approve smaller

## Expectancy in words
Adjusted odds from 20-shortlist.md: p_follow 0.456 vs p_fade 0.357 (the remaining ~0.19 is unresolved by these two numbers — chop or time-stop). Distance-wise, per 30-intraday-plans.md, target 1 (1010.9923) sits exactly the same 8.2077 points from the trigger as the stop (1027.4077) — i.e. target 1 is about 1R, not a payout trade. Target 2 (1002.7846) is about 2R. So this wins a bit less than half the time for roughly 1R (more if it runs to target 2) and loses a bit more than a third of the time for roughly 1R. That is a thin, close-to-breakeven setup whose only edge is the win-rate tilt (45.6% vs 35.7%), not the payout — there is no 2R-for-1R asymmetry baked into target 1. It only turns clearly favourable if price runs the extra distance to target 2, and nothing in the files quantifies how often that happens.

## Consistency checks (pass / fail each)
- Stop beyond a real level: pass. Stop is a 5-minute close back above VWAP 1027.4077, a defined technical level, not an arbitrary tick distance (01-tape.md, 00-scan.json).
- Time stop matches HORIZON: pass. HORIZON is intraday, square-off by 15:05 IST is the global constraint (30-intraday-plans.md header); the order itself is a break-trigger, so it either fires within the session or expires unfilled — no horizon mismatch.
- Event inside HORIZON handled: pass, trivially. 02-catalysts.md finds no substantive INFY catalyst pre- or intra-scan, only a price-recap headline — there is no event to size around.
- Target logic vs. an untested level: fail. 30-intraday-plans.md's own check flags that target 1 (1010.9923, ~57% of ADR) sits below the next daily support (1013.9, ~42% of ADR, 01-tape.md) that price has not yet traded through. The plan assumes the trade punches an untested support shelf on the way to target 1. The file's own suggested fix — scale out at/above 1013.9 first, run the balance only on a 5-minute close below it — is the more internally consistent version of this plan.
- Sizing: fail (incomplete, not a directional flaw). 30-intraday-plans.md states qty is "not sized in scan output" and total loss at stop is not computed. This is not executable as an order until capital/risk settings size it.

## Correlation
INFY's own daily tape is genuinely bearish on its own terms (-DI 33.1 > +DI 19.4, RSI14 35.1, price below all SMAs — 01-tape.md), so this is not purely an index proxy. But the reason it was selected over SBIN.NS and DIXON.NS was the market-wide tilt (03-regime.md: breadth 33.3%, index -0.26%, "favoured side: short"), and 20-shortlist.md says so explicitly when rejecting SBIN: "it is the same index-down bet as INFY on a weak tilt." There is no company-specific catalyst (02-catalysts.md) distinguishing INFY from the rest of the down-tilted tape. Net: part idiosyncratic (daily momentum), part riding a thin, coin-flip-grade index tilt (03-regime.md's own "43% follow vs 40% fade" framing). If the intent is to express the index view, a Nifty-linked instrument would carry less single-name noise (no confirmed catalyst, B-grade tape) for roughly the same thesis.

## Response to other seats (rounds 2+)
N/A — round 1.
