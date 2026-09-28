# Risk: neutral, round 1

Verdict (one per stock):
- KOTAKBANK.NS: approve
- AXISBANK.NS: reject
- PAYTM.NS: wait for trigger
- MEESHO.NS: reject

## Expectancy in words

**KOTAKBANK.NS.** Mechanical 1R at target 1, 2R at target 2 against a 1R stop (OR-defined) either side, and resistance at 410.29 sits beyond the 2x-OR reach, so the long side has room to run past target 2 rather than stalling into a level first [30-intraday-plans.md]. This is a symmetric two-sided break, not a directional edge — the case for taking it rests on tape grade A and a corporate-action catalyst the price has not absorbed yet [20-shortlist.md], not on a stated p_up/p_down split.

**AXISBANK.NS.** Same nominal 1R/2R geometry, but the short side's target run passes through support at 1221.16 before it gets there, since that level sits inside the typical opening range itself [30-intraday-plans.md]. Real reward on that side is closer to "reaction off a nearby level" than a clean 2x-OR extension. No catalyst, so it does not qualify for the day's single trade regardless of setup quality [20-shortlist.md].

**PAYTM.NS.** Same 1R/2R geometry if it ever triggers, but the entry condition (OR at or under 29.17) is already tighter than the stock's typical opening range (33.1), so on a typical day this setup does not fire at all [30-intraday-plans.md]. Tape grade C on top of that means the breakout itself is lower quality (efficiency/volume weaker than KOTAKBANK's grade A), so even conditional on triggering, the win rate behind the 1R stop is worth less than the mechanical numbers imply [01-tape.md via 20-shortlist.md].

**MEESHO.NS.** Long side's 2x-OR target runs through resistance at 223.1 before reaching it, so real reward on that side is closer to 1x-OR-to-level than a clean 2R [30-intraday-plans.md]. Short side toward support (10.31 pts away) is unobstructed. No catalyst behind the -5.26% drop, so — win/loss geometry aside — it is excluded from the day's single trade by the range-day rule [20-shortlist.md].

## Consistency checks (pass / fail each)

**KOTAKBANK.NS**
- Stop beyond a real level: pass — stop is the OR opposite side, and the level in play (410.29) sits beyond the 2R target, not inside the stop-to-target path.
- Time stop matches HORIZON: pass — square-off by 15:05 is the terminal exit; no separate time stop is stated but none is needed for an OR-break system on this horizon.
- Event inside HORIZON handled: pass — the merger/swap catalyst is dated 2026-09-25 and the market has had one session (-0.71%) to react; it is a known, already-public event, not a live release during the session.
- Range-day eligibility: pass — this is the only name on the sheet the shortlist says can meet "grade A + fresh catalyst," contingent on the live tape confirming grade A [20-shortlist.md].

**AXISBANK.NS**
- Stop beyond a real level: fail on the short side — the 2x-OR target, not the stop, runs through support before reacting to it, so the stated reward is overstated versus the actual level geometry [30-intraday-plans.md].
- Time stop matches HORIZON: pass (same square-off logic).
- Event inside HORIZON handled: n/a — no catalyst identified [20-shortlist.md].
- Range-day eligibility: fail — no fresh catalyst, so excluded from the day's single trade regardless of tape grade.

**PAYTM.NS**
- Stop beyond a real level: pass structurally (OR-defined stop), but the entry gate itself fails on a typical day — typical OR (33.1) exceeds the skip cap (29.17) [30-intraday-plans.md].
- Time stop matches HORIZON: pass.
- Event inside HORIZON handled: partial — the RBI catalyst is already two sessions old and contested by a same-day company clarification, so direction is correctly left undecided rather than assumed bearish [20-shortlist.md].
- Range-day eligibility: fail on tape grade (C), conditional pass only if the live OR prints materially narrower than typical.

**MEESHO.NS**
- Stop beyond a real level: fail on the long side — the 2x-OR target runs through resistance before reacting to it, same pattern as AXISBANK [30-intraday-plans.md].
- Time stop matches HORIZON: pass.
- Event inside HORIZON handled: n/a — no catalyst found for the move, flagged as possibly flow-driven [20-shortlist.md].
- Range-day eligibility: fail — no catalyst, excluded from the day's single trade.

## Correlation

None of the four names carry a beta/correlation figure in these files (that data appears in an analyze run's 01-market.md, not this scout run's evidence set). The closest available read is 03-regime.md: the candidate list splits evenly — two closed strong up, three strong down, three flat — with no market-wide lean and VIX unremarkable (46th percentile) [03-regime.md]. That argues against any of these being a disguised index-beta bet: each is standing on its own move and (for KOTAKBANK and PAYTM) its own stock-specific catalyst, not on a shared Nifty direction. No further correlation check is possible from the files on hand.

## Response to other seats (rounds 2+)
N/A — round 1.

Not investment advice. Public data, possibly delayed; verify before acting.
