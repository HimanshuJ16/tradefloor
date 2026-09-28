# Intraday shortlist: nifty 50, scan at 2026-09-22 11:15 IST
Trades: 1   Day verdict: selective

Rule 4 check: the regime is "trend down (weak)", not range, and `regime_read` says "No momentum edge lately: ... followed through 43% and faded 40%". Follow-through still beats fade in that read, so it does not say momentum has reversed, and rule 4 does not bind. The day is still weak. Breadth is 33.3% above VWAP, the index is -0.26%, the tape has no A grades, and every candidate's scan edge is 0.069 or less. Passing the 0.05 gate is therefore required but is not enough on its own. I select only the one setup where the regime, the daily trend and the tape all point the same way.

## Struck claims
- Skeptic, INFY.NS: "indistinguishable from noise once the calibration's own error bars are considered". Struck. 00-scan.json reports n=178 and n_effective=150.0 but no error bars or intervals, so the claim cites a figure that does not exist.
- Not struck, but noted: the skeptic uses "43.1% vs 39.5%" for "the strongest setups". Those values exist in 00-scan.json as the quintile-5 p_follow/p_fade (0.431/0.395), and they match regime_read's rounded 43%/40%. The claim stands.
- Not struck, but noted: 03-regime.md says "3 are long (... 5 long)", which contradicts itself. 00-scan.json has 5 longs and 3 shorts. The skeptic's "5 longs against only 3 shorts" is correct.
- Every other number in 10-advocate-r1.md and 11-skeptic-r1.md checks out against the file it cites: VWAPs 1027.41 / 992.21 / 424.79, triggers 1019.2 / 987.1 / 428.3, RVOL, efficiency, DI/RSI/ADX, RS +10.6%, catalyst timing of about 55 minutes, and breadth 33.3%.

## Selected
### INFY.NS SHORT
p_follow / p_fade: scan 0.436/0.367 -> adjusted 0.456/0.357; reasons:
- +0.02 p_follow: the regime runs with the short. 03-regime.md gives "Favoured side: short", breadth 33.3% above VWAP and index -0.26%.
- -0.01 p_fade: the short lines up with daily momentum. 01-tape.md shows -DI 33.1 > +DI 19.4, RSI14 35.1, 50d SMA below 200d, and price below all SMAs.
- No move for catalyst. The only headline is a price recap (02-catalysts.md). That is neutral, because the calibration base is mostly setups without catalysts.
- No move for tape. It is grade B: RVOL 1.42 is under the 1.5 bar and efficiency 0.43 is under 0.5.
- Total moved: 0.03 of the allowed 0.10. Adjusted gap: 0.099, which clears 0.05.

Deciding evidence:
1. It is the only candidate where the regime tilt (short-favoured, 03-regime.md) and the daily trend (-DI 33.1 > +DI 19.4, RSI14 35.1, 01-tape.md) both run with the trade, and the tape is not sub-average (RVOL 1.42 [00-scan.json]).
2. The scan calibrates it in quintile 4 with p_follow 0.436 vs p_fade 0.367, edge +0.069, read "follow-through tendency" (00-scan.json). The plan is trigger-based: break below the day low 1019.2, invalidated on a 5-minute close above VWAP 1027.41. This limits the risk from the 15-minute exchange delay.

## Rejected (strongest candidates only)
- SBIN.NS SHORT: adjusted 0.426/0.367 (+0.02 regime with, -0.03 for RVOL 0.89 below its own average, -0.01 fade for daily trend aligned with ADX 26.8). It clears the gate, but it relies on sub-average participation (rvol component 0.0), it has no pre-scan catalyst, and it is the same index-down bet as INFY on a weak tilt. It is out so that one thin thesis is not doubled.
- COALINDIA.NS LONG: adjusted 0.446/0.387 (+0.03 fresh catalyst with the move, -0.02 regime against, +0.02 fade for efficiency 0.25, the lowest in the batch, and a "transition" daily regime). The gap is 0.059, only just over the gate. It runs against the day's short tilt, and the catalyst from 10:20 IST is already priced into a +2.05% gap and +1.11% move.
- SWIGGY.NS LONG: scan 0.431/0.395, a gap of 0.036, which starts below the gate. The catalyst is sector-wide, the tape is choppy (efficiency 0.37), the daily regime is range-bound (ADX 12.6) and the regime runs against it.
- MEESHO.NS LONG: scan 0.431/0.395, gap 0.036, read "no edge". It is extended +2.6% from VWAP, RSI14 is 76.8, tape grade is C, and there is no catalyst.
- IDEA.NS LONG: the regime runs against it, RVOL 1.27 and efficiency 0.30 are weak, and daily -DI 23.9 > +DI 19.7. Its only catalyst came after the scan and is excluded as look-ahead.
