# Research workspace (0.5)

Run `uv run --project server python -m tradefloor.demo` and open `http://127.0.0.1:8765`.
The prior scenario view remains at `/lab`. The workspace and numerical tools work locally;
there are no accounts or broker connections. The public artifact contains synthetic data only.

## Reading the terminal

Use the three scenario cards to open an original earnings, policy or liquidity example.
The session strip records the loaded receipt's world count, horizon and seed. Selecting a
draft assumption leaves the loaded results visible until Run or Fork completes.

The chart supports return percentages and prices in the frozen reference's quote units.
Its slider and keyboard arrows select actual saved observation days; the readout includes
the scenario median, 10–90% interval and no-reaction baseline. Day zero is the frozen anchor.
The shaded interval describes conditional simulations, not a confidence interval for model
accuracy. The SIDEWAYS band is converted from the receipt's log-return event definition.

The thesis summary derives its direction, baseline probability shift and evidence counts
from the loaded receipt. It does not independently evaluate the evidence or infer causality.
Press **Ctrl+K / Cmd+K** to search views and available actions. Enter selects the first match;
Escape closes the menu. Mobile controls expand from **Project & assumptions**.

## Model connections and sessions

**Models & keys** saves a name, exact model ID, versioned API base URL and protocol.
Supported protocols are streaming OpenAI-compatible `/chat/completions` and Anthropic
`/messages`. Ollama/LM Studio and compatible gateways use the former. Models must return
the structured JSON research contract; unsupported or truncated responses remain failures.
There is no promise that every provider, model or API feature works with either protocol.
The connection test sends one fixed small prompt, not private research, and may be billable.

Use an OS credential store or a server environment-variable name. Supported vault backends
are Windows Credential Manager, macOS Keychain and Linux Secret Service. No plaintext vault
fallback is permitted. Headless systems should use environment variables. Keys are scoped
to the resolved Tradefloor data home and are never saved to SQLite, localStorage or archives.
Environment keys take precedence within a profile. Changing a stored key's destination
requires re-entering it. Redirects and proxy-environment forwarding are disabled. Custom
remote endpoints require HTTPS; plain HTTP is limited to explicit loopback addresses.
Other local processes with access to the same OS account are outside the application boundary.

**Research desk** supports Quick (researcher/risk), Balanced (researcher/bull/bear/risk),
Deep (plus synthesis), independent comparison of two to four connections, and single-role
questions. Connections can differ by role. Bull/bear answers are independent; risk/synthesis
receive earlier outputs as untrusted text. Comparison models never receive each other's answers.

Preview freezes the source receipt, eligible active evidence, numerical prior, reaction
assumptions, dated memory and available timeline records. The model context excludes the
synthetic settlement and future price path. Large contexts fail visibly at 48 KB rather
than silently dropping evidence. Follow-up questions include earlier model answers as
untrusted research on the same receipt. None of this establishes a model's training cutoff;
retrospective sessions are not prospective performance evidence.

Start submits a durable job. The worker permits at most 20 calls, 128–4096 requested output
tokens per call, 120 seconds per model request, 1 MB per stream and 64 KB of model text.
Each role can request one follow-up from five allowlisted read-only tools: evidence,
assumptions, frozen baseline probabilities, dated research memory and the information timeline.
Tools return the previewed frozen context, not a new web search or fresh market snapshot.
No shell or code proposed by a model is executed. Cancel preserves partial output; cancellation
is cooperative and an in-flight call may still be billed. Stream reads time out after 20 seconds
without data. Reclaimed interrupted model sessions stop for review; they never automatically
repeat potentially billable requests. Starting the same plan twice is idempotent.

Pricing is supplied by the user in USD per million input/output tokens. Blank means unknown,
zero explicitly means free. A cost cap requires known prices and must cover a conservative
preflight reservation. Reported token counts produce calculated cost when available; missing
usage remains unknown. Reservation uses bounded UTF-8 input sizes and prior response ceilings,
not a model tokenizer. These controls do not guarantee the provider's invoice, pricing,
special token fees or enforcement of its requested output limit.

## Reviewing model research

Claims carry evidence IDs, optional exact source excerpts and numeric reference paths.
Audits flag unknown/missing citations, absent quoted text, mismatched numbers and prose
numbers lacking structured references. A passing reference check does not establish truth,
entailment, causality or completeness; unstructured summary numbers are not verified.
Probability proposals must sum to one, cite eligible evidence for each change and stay
within 0.10 of the frozen quant prior in every class. Failed proposals remain visible and
are excluded from validated forecast comparisons. Abstentions and role failures are retained.

The disagreement view compares validated forecast directions/class gaps and displays
model-supplied assumptions, objections and proposed observations/tests. It does not automatically
prove which objection is correct or execute the proposed tests. Recipes save questions,
role routing and limits without scheduling autonomous calls.

Complete sessions can be exported with source receipts, prompts/context, activity and responses.
They contain private research and provider data but no connection credentials. Archive import
checks hashes, the original source receipt and its context, then recomputes reference audits.
Exports preserve canonical JSON in a string envelope so browser numeric formatting cannot
invalidate nested session/plan hashes.
Malformed model lists, summaries and observation proposals fail visibly before rendering.
Malformed probability adjustments remain rejected proposals rather than crashing the audit.
Closed session memory is checked against its saved seal before retrieval.
Imported research is stored separately, clearly marked untrusted, and never automatically
executed. Hashes do not authenticate an author or establish an external publication date.
Local sessions can be reopened and continued through browser, CLI or MCP contracts.

**Freeze forecasts** requires validated non-abstaining output, a future settlement close
and an explicit rule. The supplied close must be no earlier than the event's minimum calendar
horizon; the user must choose the actual exchange trading-calendar close. A local commitment
is not external preregistration. Settlement requires a matured, currently available outcome
and a source; outcomes are user-supplied rather than independently market-verified. Brier,
log-loss and reliability summaries separate synthetic and supplied-history groups. Multiple
roles on one event remain correlated forecasts. No automatic ranking, trust weight or promotion
is learned from these scores. Use `robust_evaluation` for explicit paired evaluation designs.
Score groups distinguish the connection, endpoint/protocol and requested model identifier;
identical model aliases on different connections are not merged. Older scores without that
identity are grouped separately as legacy records.

## Data hub

Import a daily CSV with 252–20,000 rows and unique ordered ISO dates. Date/Close are required;
Open/High/Low/Volume are supported. Scenario analytics require supplied High and Low; missing
intraday ranges are never invented. Imports retain the symbol, source, adjustment basis,
asserted availability and data rights. Values must be finite, prices positive, volume nonnegative.

Yahoo Finance captures are explicit provider requests, frozen at capture time. Refreshed
adjusted history does not establish an archival vintage. If a dataset was captured after its
last price cutoff, the source is labeled an availability-unverified assumption when opening
a scenario. CSV dates and source availability are asserted metadata, not proof of historical
completeness. Imported-data scenarios have no fabricated synthetic settlement.

Configure the SEC contact header and an ALFRED OS-vault/environment key in Data hub, then
fetch a selected source in Information timeline. Existing `TRADEFLOOR_SEC_USER_AGENT` and
`FRED_API_KEY` environment variables take precedence. Saving settings never fetches data.
The public static artifact disables all model, credential, dataset and mutable session controls.

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

## Research map

Research desk includes a dependency-free SVG map of the loaded scenario or selected session.
The session view uses its own frozen source receipt even when another scenario is loaded.
Nodes distinguish evidence/assumptions, scenario interpretations, research roles, read-only
tool receipts, audited model claims, conditional forecasts, objections and proposed tests.
Edges show the recorded relation: supplied evidence support/dependency/contradiction,
agent-produced output, cited references or explicit adjustment references. Forecast comparisons
are recomputed from visible audited forecasts, including imported sessions; a difference in
probabilities does not establish one forecast's superiority.

Select a node for exact records and its explicit neighbors. Search and category filters,
review/disagreement filtering, neighborhood focus, background pan and zoom provide navigation.
Keyboard selection and a complete list provide an alternative to the diagram. The rendered
map is limited to 160 nodes and 1,200 lines, prioritizing selected-node connections; the list
and inspector retain the full matching records. Cinematic mode adds decorative stars/glow
and animated lines; reduced-motion settings disable animation. It does not visualize model
attention or undisclosed reasoning.

Replay advances through recorded events. Final claims/forecasts appear at their response
checkpoint, not before it. Stream text is the last saved snapshot for that call; the backend
does not retain token-by-token history. Replay stops when leaving the desk or hiding the page.
Cancelled and failed sessions retain completed output and show unfinished roles separately.
Imported archives remain visibly untrusted; their origin and timing are not independently verified.

**Preview withdrawal impact** traces only explicit dependency/reference links. It does not
estimate a causal effect or recalculate probabilities. **Create branch with evidence retracted**
creates a new local scenario receipt with an immutable parent, identical price history and
numerical assumptions, and the selected input retracted. Dependent scenario claims are marked
for review; a new research plan excludes that retracted input. It does not edit the original
session or run providers. Imported session maps and the static demo cannot create branches.
The static demo retains map inspection, filters and navigation on its frozen scenarios.

## Sources and cited reports

`research_library` lists, imports, opens and searches immutable local documents. Text and
Markdown are preserved as text; HTML scripts/forms/styles are excluded. PDF extraction runs
in a separate process with a 20-second timeout. Limits are 5 MB of raw input, 200,000 extracted
characters, 200 PDF pages, 250 documents and 100 MB of serialized library records. Encrypted,
scanned, malformed and oversized PDFs fail visibly. OCR is not included; extracted PDF text
and table layout need user verification. A worker timeout is not a complete malicious-PDF
sandbox or a strict memory guarantee.

Original bytes and extracted text have separate hashes. Exact extracted-text spans retain
character offsets; a span does not assert the fidelity of PDF extraction to the original
visual page. Local BM25 ranking returns up to 50 matching passages, with date eligibility
against the loaded scenario. Relevance and content hashes do not establish source truth.

Select up to 20 passages to preview and freeze into a new child scenario. Both publication
and availability must be known and no later than the original cutoff. These dates are asserted;
retrieving a document today does not establish its past version. Freezing preserves prices,
numerical assumptions and the parent receipt. Exact anchors remain in the receipt; model
context includes the selected passage and hashes, not the entire underlying document.
The 48 KB context limit still applies. New sources are sent only after plan preview and Start.

`source_discovery` explicitly discovers recent SEC filing metadata or captures a selected
public document. SEC uses the Data hub contact. Captures allow public HTTPS on port 443,
reject credentials/query strings/private addresses, pin the validated IP while preserving
TLS hostname verification, and do not follow redirects. At most 5 MB is downloaded.
This is a capture interface, not an unrestricted autonomous web-search or archival feed.
Source redistribution rights remain the user's responsibility.

`research_report` produces structured records, escaped Markdown and printable HTML from a
scenario/session. It includes the question, provenance, numerical assumptions, conditional
forecasts, structured claims/references, rejected adjustments, observations and source appendix.
No synthetic settlement or future path is included. Reports retain failure/abstention and
import trust status; passing reference checks do not establish meaning or predictive skill.
The UI supports report preview, downloads and browser Print / Save as PDF. The standalone
demo supports fictional source inspection and scenario report export; it cannot import
documents, capture sources or freeze evidence.

## Deployment boundary

The local server is single-user loopback software with strict Host/Origin checks. It has no
tenant isolation or public credentials system. Deploy the standalone synthetic artifact;
do not expose the local server to the Internet. `.github/workflows/pages.yml` is a manual
static deployment workflow, requiring repository Pages configuration and a reviewed revision.
No public deployment is performed by installation or local startup.
