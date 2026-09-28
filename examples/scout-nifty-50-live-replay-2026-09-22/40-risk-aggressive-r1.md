# Risk: aggressive, round 1

Verdict: INFY.NS SHORT — approve

## Argument
- The stop is not manufactured caution — it's a real level. 30-intraday-plans.md's own check puts the stop 8.2077pts (~40% of the 20.66pt ADR) above the trigger, wider than a single 5-minute bar, and it sits at VWAP 1027.4077, a structural invalidation point, not an arbitrary tick buffer. Downside is already bounded by the plan; there's nothing here to trim size for.
- This is the one setup where everything lines up, and the desk already did the concentration work for me. 20-shortlist.md explicitly cut SBIN.NS SHORT — a same-side, same-index bet — "so that one thin thesis is not doubled." That argues for full configured size on INFY, not a smaller stake spread thinner across correlated shorts.
- The macro case for cutting size on volatility grounds doesn't hold. 03-regime.md: India VIX at 11.0, 19th percentile, falling — "not a risk-off setup... no need to cut size for volatility." Whatever caution the thin calibration edge justifies, it isn't a vol-based haircut.
- No event risk to size down for either: 02-catalysts.md shows only a neutral price recap, and 20-shortlist.md notes the calibration base is mostly no-catalyst setups — this trade sits squarely in the base case the numbers were built on.
- Where I'd refuse to go bigger: RVOL 1.42 and efficiency 0.43 are both grade B, under the 1.5/0.5 bars (30-intraday-plans.md, 00-scan.json), and the adjusted edge is a thin 0.099 on a day the regime report itself calls "no momentum edge lately" (43% follow vs 40% fade). That's a case against a pyramid add on a first push through 1019.2 — the entry trigger already requires confirmation (a break of day low), so treating any early print as an add-on signal would be sizing past what a grade-B tape supports. Full size at the trigger, no add beyond it.
- One real blocker, not a risk-appetite call: 30-intraday-plans.md line 10 flags no quantity/capital sizing computed yet. That has to be resolved before this is executable — it isn't the risk seat asking for less, it's the plan being incomplete.

File: tradefloor-runs/scout-nifty-50/2026-09-22-1115/40-risk-aggressive-r1.md
