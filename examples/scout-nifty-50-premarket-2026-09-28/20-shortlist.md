# Intraday shortlist: nifty 50, scan at 2026-09-27 16:31 IST (premarket, target session 2026-09-28)
Trades: 0 (premarket watchlist: 4)   Day verdict: selective

Regime is range with no favoured side [03-regime.md], and all 8 candidates have `lean: null` [00-scan.json]. Nobody gets a side before the open. At the open the range-regime rule applies: **at most one trade, and only a live tape grade A with a fresh catalyst.** On the evidence here, only KOTAKBANK.NS can meet that bar. PAYTM.NS has the catalyst but a C tape grade. AXISBANK.NS and MEESHO.NS grade A but have no catalyst.

Continuation after strong days is 0.441 on n_effective 114 [00-scan.json]. That gives a standard error of about 0.047, so the rate sits about 1.3 SE below 0.5. That is within noise, as the scan says. The regime and skeptic files call it "below a coin flip", which overstates it as evidence of reversal. It is no edge either way.

## Struck claims
- **03-regime.md, "three (AXISBANK, M&M) closed strong up"**, repeated in 11-skeptic-r1.md ("three closed strong up"). The scan shows two strong-up names: AXISBANK +2.47% and M&M +1.87%. TCS at +0.68% is flagged "No strong move yesterday". The regime split of 2+3+2 also leaves out TCS, so it does not add up to 8. Corrected: 2 strong up, 3 strong down, 3 no strong move [00-scan.json].
- **01-tape.md, "in_play_score 0.744 vs 0.85+ for bucket 9-10"**, repeated in 11-skeptic-r1.md. ICICIBANK is bucket "9 of 10" with in_play_score 0.769 [00-scan.json]. The conclusion still holds: M&M's 0.744 is below every bucket 9-10 name. The 0.85+ figure is wrong.
- **10-advocate-r1.md (PAYTM), "Elevated ADR (3.49%) means even a partial continuation clears the big-move bar."** The scan defines a big move as a high-low range of at least 1.3x the 20-session average range. For PAYTM that is about 4.5% (1.3 x 3.49) [00-scan.json]. A partial continuation does not clear it by definition. Unsupported.
- **02-catalysts.md / 10-advocate-r1.md, PAYTM "crash over 7%" used as a 2026-09-25 fact.** The headline is quoted correctly, but the scan's own numbers do not support it. The implied prior close is 1674 / (1 - 0.0352) = 1735.1, and the 09-25 low of 1658.8 is only 4.4% below that [00-scan.json]. No 7% drop shows in the scanned session. The date and size of the catalyst are unverified, so it is discounted, not ignored.
- **01-tape.md / 10-advocate-r1.md, MCX "3.16% off the 52-week high (3433.29)".** This conflicts with the scan's prev_high of 3478.7 on 2026-09-25 [00-scan.json], which is above the stated 52-week high. The level can't be checked from the files. It is also irrelevant to the advocate's down-side call.

## Selected (opening watchlist, ranked by adjusted p_big_move)

### 1. AXISBANK.NS either, decided by the opening range
p_big_move: scan 0.331 -> adjusted 0.331. Reasons: no move. There is no catalyst beyond price commentary ("treat as technical") [02-catalysts.md].
p_continuation 0.441, lean null. No side [00-scan.json].
Deciding evidence: highest lift on the sheet, 1.76x the 0.188 base, bucket 10 of 10 [00-scan.json]. Typical opening range is 6.85 against a skip cap of 10.37, so the plan works in both directions [00-scan.json][01-tape.md].
Watch: last close 1222.4 sits on support at 1221.16 [01-tape.md]. The daily trend is down (50 SMA below 200) [01-tape.md], so an upside break fights the daily trend. Skip if the opening range is wider than 10.37, or if price gaps past 1224.5 / 1191.7 and reverses back in [00-scan.json].

### 2. PAYTM.NS either, decided by the opening range (conditional)
p_big_move: scan 0.234 -> adjusted 0.284. Reasons: +0.05 for a fresh regulatory catalyst (RBI cancelling the Payments Bank licence, 2026-09-25) that is still open, since the company put out a clarification the same day [02-catalysts.md]. Unsettled stories raise the odds of a wide-range session. The adjustment is capped at +0.05 because the headline's size does not match the scan (see Struck claims).
Side: the advocate's down call is rejected. The scan gives continuation 0.441, which is a coin flip [00-scan.json]. The catalyst is bearish, but the clarification and the 7% vs 4.4% mismatch mean it does not clearly imply a direction. A break below the opening range would be consistent with the story. The break decides, not the story.
Deciding evidence: the only candidate with a fresh regulatory catalyst in the direction of its move, closing -3.52% at close_location 0.17 [02-catalysts.md][00-scan.json]. Tape grade C: the typical opening range of 33.1 is above the plan's skip cap of 29.17 [01-tape.md].
Condition: watch only unless the opening range prints at 29.17 or less. Otherwise the plan's own skip rule applies [00-scan.json].

### 3. KOTAKBANK.NS either, decided by the opening range
p_big_move: scan 0.234 -> adjusted 0.264. Reasons: +0.03 for a fresh corporate action (board approved the KMIL/KAAML merger at a 7:6 swap ratio, 2026-09-25) that the price has not yet absorbed: Friday's move was only -0.71% [02-catalysts.md][00-scan.json]. The catalyst desk calls the direction unclear, so no side [02-catalysts.md].
Deciding evidence: traded value was 1.47x average, the highest on the sheet, on a small move, which suggests positioning around the news [00-scan.json]. Tape grade A: the typical opening range of 2.425 is under the 3.105 cap, and resistance at 410.29 is within big-move reach (6.29 pts vs about 8.1) [01-tape.md].
Range-day note: this is the only watchlist name that can meet the "A plus fresh catalyst" bar for the day's single trade. The live grade must confirm it. Skip if the opening range is wider than 3.105, or if price gaps past 407.95 / 399.45 and reverses [00-scan.json].

### 4. MEESHO.NS either, decided by the opening range
p_big_move: scan 0.234 -> adjusted 0.234. Reasons: no move. No catalyst was found for the -5.26% day [02-catalysts.md]. An unexplained drop does not earn a catalyst adjustment.
p_continuation 0.441, lean null [00-scan.json].
Deciding evidence: closed at the low (close_location 0.07) on 1.54x its average range [00-scan.json]. Levels sit on both sides within reach, resistance at 223.1 and support at 206.75, and the typical opening range of 3.65 is under the 4.196 cap [01-tape.md].
Caution: the move is unexplained and could be flow-driven [02-catalysts.md]. It is not eligible for the single range-day trade without a fresh catalyst.

## Rejected (strongest candidates only)
- ICICIBANK.NS: 0.234 with no catalyst (open-interest chatter only). Tape grade B and marginal on both counts: opening range 9.4 vs cap 9.035, and the level is 24.51 pts away vs 23.46 reach [01-tape.md]. It adds nothing over the four above.
- MCX.NS: 0.234, tape grade C (opening range 56.85 vs cap 52.14) [01-tape.md]. The gold-futures sector headline does not clearly point MCX's own shares in either direction, so the advocate's down side is not kept. Its 52-week-high level is unverifiable (struck).
- M&M.NS: 0.234, bucket 8 of 10, p_trend_day 0.30 vs 0.348 for the top names [00-scan.json]. The Q2 results date is unconfirmed and could fall in the target session [02-catalysts.md]. That is event risk, not a catalyst to adjust for.
- TCS.NS: 0.218, bucket 7 of 10, grade C, no level within reach, no headlines [01-tape.md][02-catalysts.md].

Not investment advice. Public data, possibly delayed; verify before acting.
