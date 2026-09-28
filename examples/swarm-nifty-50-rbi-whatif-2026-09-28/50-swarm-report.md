# Swarm report: ^NSEI (NIFTY 50), horizon 1m, as of 2026-09-28
2,000 simulated traders in 6 groups, 1,000 worlds over 21 trading days, calibrated to daily vol 0.835% (tail df 6.4, normal drift +0.049%/day) [swarm_simulate].

All six baseline persona files and all six what-if persona files carried a valid reaction block; no group is missing.

| | p(up) | p(down) | p(flat) | median | 80% range |
|---|---|---|---|---|---|
| Normal behaviour (baseline) | 51.8% | 28.6% | 19.6% | +1.09% (23,043) | -3.98% to +6.52% (21,887 to 24,280) |
| With the crowd's reactions | 49.3% | 30.3% | 20.4% | +0.91% (23,001) | -4.16% to +6.32% (21,846 to 24,235) |
| Quant model (history of similar setups) | 57.5% | 23.3% | 19.3% | +2.62% (raw median of similar setups) | 22,017 to 24,285 |
| What-if: W1, RBI hikes repo 25 bp to 5.50% on 7 Oct | 42.4% | 36.3% | 21.3% | +0.25% (22,850) | -4.79% to +5.63% (21,703 to 24,076) |

Shift from the crowd vs baseline: p(up) -2.5 pts, p(down) +1.7 pts, median -0.18%. Shift from the what-if vs baseline: p(up) -9.4 pts, p(down) +7.7 pts, median -0.84% [swarm_simulate].
Quant model: price 22,794, setup score -0.575 (bearish), base rates up 53.0% / down 27.1% / flat 20.0%, 1-sigma horizon move 3.82%, direction UP, confidence low, 25 effective similar setups [direction_forecast].

## Who moved the price
| Group | Reaction (sentiment, conviction, persistence) | Moved the price (scenario) | Moved the price (what-if W1) |
|---|---|---|---|
| Domestic funds and insurers (dii) | +0.30, 0.45, 18 d (fair value +9%) | +0.58% | +0.27% (+0.10, 0.35, 15 d, FV +4%) |
| Foreign institutions (fii) | -0.50, 0.60, 12 d (fair value -6%) | -0.44% | -0.55% (-0.55, 0.55, 15 d, FV -8%) |
| Retail traders (retail) | -0.65, 0.55, 2 d (fair value -8%) | -0.23% | -0.38% (-0.75, 0.60, 3 d, FV -12%) |
| Prop and algo desks (prop) | -0.35, 0.45, 2 d | -0.08% | -0.13% (-0.55, 0.60, 2 d) |
| Event funds (event) | -0.10, 0.20, 2 d (fair value -3%) | -0.02% | -0.06% (-0.45, 0.55, 3 d, FV -6%) |
| Market makers (mm) | +0.20, 0.30, 2 d | +0.01% | +0.01% (-0.10, 0.35, 2 d) |

Why: DII sees the 200-week MA test and oversold readings as its scaling-in zone and keeps SIP money coming; FII sees the dollar, US yields and crude all working against India's allocation and keeps trimming; retail sells the "crash" headlines but its conviction burns out in about two days.

## Read
The crowd barely moves the odds. With the six groups' reactions, p(up) falls 2.5 points and p(down) rises 1.7 points against normal behaviour. Both changes are under 3 points, which is noise at this sample size. The groups mostly cancel each other out: patient DII dip-buying (+0.58%) roughly offsets persistent FII selling (-0.44%), and the retail and prop selling is short-lived (2-day persistence) and fades well before the month is out. The quant model leans more to the upside (57.5% up vs a 53.0% base rate) because on this index, similar bearish, deeply oversold setups have historically mean-reverted. But its confidence is low, it rests on about 25 effective samples, and it cannot see news. So the crowd and the model agree on direction (up is more likely than down, mostly because the index normally drifts up) and disagree on strength: the crowd sits slightly below normal behaviour and the model slightly above it. The what-if is the one result that clears the noise. A 25 bp hike on 7 October moves p(up) down 9.4 points and p(down) up 7.7 points, cuts the median to +0.25%, and leaves up and down close to even (42.4% vs 36.3%, which would count as SIDEWAYS under the journal rule). Most of that comes from the hike removing DII's cushion (its push drops from +0.58% to +0.27%) while FII and retail selling gets heavier. None of this is a prediction: it is the spread of outcomes given the index's normal behaviour and these reactions.

## What would change it
- RBI on 7 Oct: a hike moves the odds to roughly even (see the what-if row). A hold, or dovish guidance with a hike, keeps the scenario near baseline.
- Crude, US 10-year yields and the rupee: if they roll over, FII's -6% fair-value view loses its basis and the largest negative push goes away.
- A break of the 52-week low at 22,331.40 with continued FPI outflows: DII says it would slow its buying, which removes the main positive push.
- Q2 earnings from TCS (8 Oct) through HDFC Bank and Axis Bank (17 Oct): margin surprises in either direction would reset the FII and event-fund reactions.

Journal: 136b9c42efe0 (source swarm). Recorded as UP, with p(up) 0.493 and p(down) 0.303 from the crowd scenario, base p(up) 0.53 and flat band 0.955%. The what-if is hypothetical and was not recorded. Not investment advice. Public data, possibly delayed; verify before acting.
