# Research lab guide

Start `uv run --project server tradefloor-demo`, open http://127.0.0.1:8765. The seven UI
presets are small experiments; CLI/MCP expose continuous parameters and frozen user data.
Run `tradefloor list` for current signatures.

## Frozen experiments

```bash
uv run --project server tradefloor scenario_lab case=earnings sentiment=0.6 persistence=5 worlds=300
uv run --project server tradefloor scenario_fork run_id=YOUR_32_HEX_ID --file fork.json
uv run --project server tradefloor run_replay run_id=YOUR_32_HEX_ID
uv run --project server tradefloor run_bundle run_id=YOUR_32_HEX_ID
```

`fork.json`:

```json
{"overrides":{"sentiment":-0.6,"persistence":1,"retail_weight":0.1}}
```

Bundles save inputs, runtime versions, source hash and results. A compatible model/runtime
is required for replay; seeds do not promise identical floating-point results across all
platforms/versions. The original is preserved and replays get new IDs. Parent links show
local lineage, not causal proof.

To import a downloaded bundle, create `import.json` with `{"bundle": <bundle object>}` and
call `tradefloor run_bundle --file import.json`. Browser exports preserve the original
canonical JSON bytes. Standalone-file imports are unverified previews.
MCP clients can supply `bundle_json` as the original JSON text to retain numeric types;
parsing/reserializing in JavaScript can turn integral floats into integers and change a hash.

## Your own history

Supply `price_snapshot` to `scenario_lab`:

```json
{
  "schema":"ohlcv-v1",
  "index":["2026-01-01T00:00:00","2026-01-02T00:00:00"],
  "columns":["Open","High","Low","Close","Volume"],
  "rows":[[100,102,99,101,1000],[101,103,100,102,1200]],
  "adjustment_basis":"describe your adjustment vintage",
  "rights":"describe your license"
}
```

This shape example has too few observations to run. Supply at least 41 ordered unique
daily observations, finite values and positive Close; at most 20,000 rows. Years of history
are preferable for calibration. Only supported OHLCV/action columns are accepted. User
availability and data rights are not independently verified.

## Evidence and decisions

`evidence_audit` accepts unique IDs and kind source/measurement/assumption. Sources and
measurements require timezone-aware published_at and available_at no later than cutoff.
Claims cite known evidence_ids. Exact normalized duplicate text is flagged; correlated
or syndicated sources can still escape this simple deduplication.

Full-desk journaling requires quant_prior (up/down/flat), evidence and aggregate
adjustments. Each change has class, delta, reason and evidence_ids. Final classes stay
within 0.10 of the original prior, summing to one. `decision_validate` computes direction.
Arithmetic/reference validation cannot establish factual truth.

Copy the daily event_contract exactly. It records as_of, horizon_days, reference_price,
log convention and a band from 63-session volatility. Do not reconstruct from displayed
range volatility. Legacy entries retain simple-return contracts; report old/new cohorts
separately.

## Evaluation

`forecast_evaluation` cases have as_of, probabilities, reference and outcome
(UP/DOWN/SIDEWAYS), referring to identical events. Loss differences cluster by date.
Intervals are normal approximations, limited by small samples and overlapping horizons.

`learning_review` requires label_end on every training case. All holdout dates must follow
all training outcomes. Both periods require at least 30 date clusters and an improvement
interval below zero to become candidates for manual review. This heuristic does not
correct serial dependence/multiple testing and never deploys a learned model.

`experiment_capture` registers quant and no-reaction swarm on the same frozen history,
retaining failures. `experiment_mature` appends unofficial provider outcomes;
`experiment_settle` accepts explicitly unverified manual outcomes. The scoreboard compares
models only on matching contracts/settlements. Externally timestamp commitments before
outcomes for public prospective claims. No public upload happens automatically.

## Sizing and paper accounting

Configure account_currency with capital. Foreign quotes require fx_to_account and current
fx_as_of. Minor units need quote_unit_scale (e.g. 0.01 pence to pounds). Multiplier and
quantity_step control unit arithmetic. Missing metadata blocks sizing. Continuous futures
need a contract-specific adapter and are not sized; historical adjusted references are
not executable prices.

Costs are supplied round-trip basis points; slippage is per side, not a measured liquidity
estimate. Paper fills prefer stop on ambiguous bars, handle adverse gaps and square-off,
and exclude pre-confirmation pullback targets. Continuation uses signal_price and ADR at
the actual session close. These OHLC approximations are not real fills.
