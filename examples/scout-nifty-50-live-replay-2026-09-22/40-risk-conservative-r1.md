# Risk: conservative, round 1

## Verdict
INFY.NS SHORT: approve smaller (0.5x)

## Argument
- The feed itself is 15 minutes delayed (03-regime.md: "treat any live-looking level as up to 15 min stale"). This is a break order on day-low 1019.2 — on a stale feed, real-time price can already be through the trigger and running toward the stop before the system acts on it. That is execution risk on top of market risk, and no amount of stop discipline in the plan fixes a lagged read.
- Evidence quality is thin by the desk's own admission. 03-regime.md: base follow-through this scan is 42.5% over 890 samples, and "essentially a coin flip once cost and slippage are netted out." The selected trade's adjusted edge (0.456 p_follow vs 0.357 p_fade, gap 0.099 per 20-shortlist.md) clears the gate but sits on a foundation the regime analyst itself calls no real edge. Tape grade is B, not A: RVOL 1.42 is under the 1.5 bar and efficiency 0.43 is under 0.5 (30-intraday-plans.md / 20-shortlist.md) — sub-average participation on the one trade taken.
- Target 1 is flagged as structurally optimistic in the trader's own file: 1010.9923 sits below an untested support shelf at 1013.9 that price has not yet tested (30-intraday-plans.md, "Checks"). First profit-taking is planned through a level that hasn't proven it will break, which overstates the credit this plan should get for reward.
- No position size exists yet. 30-intraday-plans.md states plainly: "Qty/size gap... Size must come from the user's capital and intraday risk settings before this can be an executable order." Approving anything beyond a capped, conservative size before sizing is computed is approving a blank check.
- Liquidity/access is not the binding constraint here — INFY.NS is a liquid Nifty 50 F&O name, intraday short via MIS carries no unusual short-sale or circuit-limit concern. The risk in this trade is evidence thinness and feed lag, not access.

## Condition for full size
Full size only if: (1) the entry engine confirms the break of 1019.2 against a real-time (not exchange-delayed) price feed or otherwise builds in a buffer for the 15-minute lag, (2) the trader adopts 1013.9 as the first scale-out per its own alternate suggestion rather than banking on 1010.9923 as target 1, and (3) computed position size sits inside a defined per-trade risk budget before the order is live. Absent all three, 0.5x is the ceiling.

## Response to other seats
N/A — round 1.
