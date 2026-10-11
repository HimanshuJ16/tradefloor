# Research workspace (0.3)

Run `uv run --project server python -m tradefloor.demo` and open `http://127.0.0.1:8765`.
The prior scenario view remains at `/lab`. The workspace and numerical tools work locally;
there are no accounts or broker connections. The public artifact contains synthetic data only.

## Research loop

1. Open an example, name a question and save a project.
2. Edit reaction, half-life and retail share; fork the loaded run.
3. Compare two to four branches on identical frozen prices/event definitions.
4. Search for a counterexample. The distance-ordered finite grid has a bounded trial budget.
   A found point is nearest within that grid, not a continuous global optimum. No reversal
   found does not establish robustness. Behavioural and Monte Carlo uncertainty remain.
5. Copy run evidence into the project. Inspect, add or retract evidence; dependent claims
   become review-required. Freeze edited evidence into a new branch explicitly.
6. Compare model forecasts, inspect the information timeline and preserve/export the project.

Evidence text does not automatically move probabilities. A new evidence branch preserves
the numerical assumptions until the researcher explicitly changes them. Imported content
is rendered as text and cannot execute instructions or code.

## Projects and archives

`research_project` supports `list`, `create`, `get`, `update`, `attach`, `history`.
Updates and attachments require the current `body.revision`; stale saves fail visibly.
Prior revisions remain in SQLite. Run receipts remain immutable; no archive overwrites an
existing run with different content. Full archives preserve ancestors and canonical bundle
strings so JavaScript cannot alter hash-significant numeric encodings.

`project_bundle(project_id=..., include_data=false)` exports a summary without source text
or data. Full archives explicitly include private research and provider data. Review source
rights before sharing. Imports create a new project ID. They are bounded to 20 MB, 100 project
runs and 200 receipts including ancestors. Run imports in the browser retain a 2 MB limit.

## Evidence schema transition

`tradefloor-evidence-v2` replaces misleading `independent_evidence_count` with
`unique_text_count`, `source_family_count`, `source_families` and `independence_status`.
Distinct families do not prove statistical independence. Sources and measurements require
timezone-aware publication and availability timestamps. Assumptions are explicitly typed.
Claim fields: `id`, `text`, `evidence_ids`, optional `depends_on` and `contradicted_by`.
Dependency cycles and unknown IDs fail validation. Retractions propagate for review.

Optional evidence `anchor` contains `document_text`, `start`, `end`; the exact slice must
equal evidence `text`. `document_sha256`, if supplied, must match. `document_changes`
returns exact changed spans and hashes, without judging financial materiality.

Existing run-v1 receipts keep their original hashes; they are not rewritten to evidence-v2.
Import now validates their kind-specific numerical/rendering contracts. Malformed historical
receipts may consequently be rejected. Content integrity, source availability, authorship,
recomputation and publication time are separate claims.

## Jobs and recovery

The local server owns one bounded worker. Jobs persist in SQLite with queued/running/
completed/failed/cancelled states, idempotency keys and leases. Heartbeats renew long-running
work. Expired leases are reclaimed after 120 seconds. A restarted job recomputes from saved
arguments; this is retry recovery, not continuation from an arbitrary Python instruction.
Counterexample searches report candidate progress and check cancellation between candidates.
Other work observes cancellation at completion; an in-flight provider read may finish and
save immutable data. Cancellation never removes existing research.

CLI/MCP users can submit with `research_job` and process one job using `action=work`; the
CLI does not secretly launch a permanent worker. Only allowlisted first-party operations run.
Proposals and imported documents never become executable scripts.

## Real information and providers

`information_timeline` appends immutable records and selects the latest eligible revision
per series/observation/source at a cutoff. Unknown and later availability are excluded.
Freeze the returned records/hash when creating a historical experiment: later ingestion can
discover a previously missing record and therefore change a newly issued historical query.

- SEC: `archival_fetch provider=sec identifier=320193`. Set
  `TRADEFLOOR_SEC_USER_AGENT` to an application name and your contact email. Captures recent
  filing metadata and acceptance timestamps; it does not fetch historical filing bodies or
  treat current company-facts aggregates as archived fundamentals.
- ALFRED: set `FRED_API_KEY`; call `archival_fetch provider=alfred identifier=CPIAUCSL vintage=2026-09-28`.
  Captures at most 5000 observations. The vintage becomes eligible conservatively at the end
  of that UTC date. It does not certify intraday release timing. Series-specific rights apply.

Requests are rate-spaced, bounded and time-limited. Credentials remain in the server
environment; provider errors omit URLs that could contain credentials. No source is fetched
until a user/tool asks for it. Connector tests use controlled fixtures; configured live canaries
are a separate release check.

## Model and decision research

`forecast_arena` runs quant, IID bootstrap, zero-drift EWMA/Gaussian and independent Student-t
baselines on a frozen price receipt. Forecasts carry a shared event, model version, provenance,
latency and cost. This is a set of predictions, not a skill leaderboard. Optional external
forecast receipts use `tradefloor-forecast-v1`; see [extension contracts](extensions.md).

`robust_evaluation` adds moving-block intervals for paired Brier/log loss and reliability
bins for all three classes. Block length is in ordered observation dates; choose it for the
dependence structure and inspect sensitivity. Short samples return no block interval.
Reported intervals are not corrected for multiple trials. The tool never authorizes promotion.

`research_record` accepts immutable assessments, outcomes, protocols, publication witnesses
and experiment proposals. Protocols set the universe, schedule, endpoint, settlement rule,
training horizon, holdout start and trial budget. Proposals consume that budget even if they
fail. Witness URLs remain explicitly unverified until an independent verification process
is performed. There is no fabricated public track record.

`research_memory` restricts both original availability and local recording time. Backdated
claims cannot enter an earlier replay. Scores are descriptive; model reputation is not
automatically learned from small samples. `research_priority` ranks one-at-a-time endpoint
sensitivity; it does not claim expected value of information or account for interactions.

## Financial extensions

- `factor_stress`: explicit common factor shocks transmitted through supplied loadings.
  All holdings need every factor exposure, including zeros, and matching account currency.
- `portfolio_allocate`: capped, long-only, fully invested minimum variance with PSD covariance,
  convergence diagnostics and bounded iterations. No returns, taxes or execution costs inferred.
- `option_implied`: lognormal constant-volatility risk-neutral probabilities and an ATM European
  call benchmark. Supplied volatility is not a calibrated options surface or physical forecast.
- `market_diagnostics`: synthetic versus supplied measured tape volatility and spreads.
  Descriptive comparison does not establish realistic impact or calibrated microstructure.

## Deployment boundary

The local server is single-user loopback software with strict Host/Origin checks. It has no
tenant isolation or public credentials system. Deploy the standalone synthetic artifact;
do not expose the local server to the Internet. `.github/workflows/pages.yml` is a manual
static deployment workflow, requiring repository Pages configuration and a reviewed revision.
No public deployment is performed by installation or local startup.
