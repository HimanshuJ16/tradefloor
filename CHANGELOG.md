# Changelog

## Unreleased

Changed
- Replaced em dashes and their HTML/Unicode encodings with plain hyphens throughout
  project documentation, archived examples and browser labels/placeholders.
- Added the missing 0.4.0 and 0.5.0 release history below.

## 0.5.0 (2026-10-12)

Added
- Immutable local text, Markdown, HTML and text-based PDF source library with original-byte
  and extracted-text hashes, exact character spans and BM25 passage search.
- Explicit SEC filing discovery and bounded public HTTPS document capture, with public-IP
  connection pinning, TLS hostname verification and date/redistribution-rights review.
- Reviewed passages frozen into a child scenario on unchanged prices and numerical
  assumptions before a separate model-context preview and Start.
- Cited research reports with forecast structures, reference audits, unresolved observations
  and exact source appendices. Markdown/HTML downloads and browser Print / Save as PDF.
- Fictional source inspection and scenario report export in the standalone demo.
- Three shared CLI/MCP tools: `research_library`, `source_discovery` and `research_report`
  (64 tools total), plus a packaged stdio MCP smoke workflow.

Changed
- Evidence branches now attach to the active saved project.
- Updated host manifests, package version, README and release documentation for 0.5.0.
- Published and browser-verified the synthetic-only GitHub Pages demo and release artifacts.

Validation: 233 Python tests, 23 frontend tests and the GitHub OS/Python matrix passed.
The packaged MCP workflow, real public-document capture and desktop/mobile public demo
were checked. Cloud model calls remained skipped; model-driven host sessions, forecasting
skill and historical source completeness remain unverified. Scanned PDFs require a verified
text transcription; extraction is time-bounded, not a complete malicious-document sandbox.

## 0.4.0 (implemented 2026-10-12)

Added
- User-selected model profiles for streaming OpenAI-compatible Chat Completions and
  Anthropic Messages, including compatible local endpoints and per-role routing.
- OS credential-store or named environment-variable keys, explicit connection tests,
  frozen-context/destination previews, usage limits and supplied-price cost estimates.
- Bounded model research sessions, read-only tool receipts, streamed activity, cancellation,
  saved transcripts, independent comparisons, follow-up questions and reusable recipes.
- Structured quote/numeric-reference audits, bounded probability adjustments, disagreements,
  objections and proposed observations to resolve them.
- Portable session archives, cutoff-safe memory, future local forecast commitments,
  supplied-outcome Brier/log-loss scoring and reliability bins.
- Daily CSV import, explicit Yahoo history capture and SEC/ALFRED source settings.
- Interactive research map with exact-record inspection, search, filters, neighborhood focus,
  zoom/pan, cinematic/reduced-motion views, accessible lists and recorded checkpoint replay.
- Evidence-withdrawal previews and immutable child receipts with dependent review flags.

Fixed
- Malformed model-response handling, sealed-memory verification, credential rotation and
  score grouping for distinct connections that share a model alias.
- Early-load preview races and browser archive number serialization.

This work shipped with 0.5.0; no separate 0.4.0 release tag was published.

## 0.3.0 (prepared 2026-10-11)

- Persistent responsive research workspace: projects, revision history, branch comparisons,
  full archives, evidence inspection and independently frozen evidence revisions.
- Distance-ordered finite-grid counterexample search and endpoint sensitivity priorities.
- Evidence lineage, exact document anchors, source families, contradiction/retraction
  propagation and bounded document changes with exact character spans.
- Immutable information vintages with as-of selection; SEC submissions metadata and ALFRED
  vintage fetchers. Live provider credentials and availability assertions remain explicit.
- Four-model forecast arena, external forecast interchange, paired moving-block loss
  intervals and all-class reliability. No automatic model promotion or skill claim.
- Immutable agent assessments/outcomes, cutoff-safe memory, protocols, trial budgets and
  explicitly unverified witness receipts.
- Factor shock arithmetic, constrained minimum-variance allocation, constant-volatility
  risk-neutral option benchmark and descriptive tape comparison.
- SQLite jobs with idempotency, leases, heartbeat, progress, cancellation and crash retries;
  stronger semantic bundle validation and manual static GitHub Pages deployment workflow.
- 54 CLI/MCP tools. Heavy external research engines remain interchange targets, not bundled
  or verified native integrations. See `docs/extensions.md`.

Migration: existing run receipts are not rewritten. New evidence graphs use v2; older run
formats remain readable subject to semantic validation. Back up TRADEFLOOR_HOME before
upgrading. The browser server remains loopback-only and is not a multi-user hosted service.

## 0.2.0 (prepared 2026-10-10)

- Offline scenario lab and synthetic browser demo, standalone HTML export, evidence graph,
  assumption sweeps, falsification, frozen replay/forks and verified bundles.
- Experimental constrained price-time order book, conserved cash/inventory and ledger tests.
- Shared log-return event contracts; correct binary and multiclass scores, paired references,
  date-clustered evaluation and untouched holdout gates.
- Probability/decision validation, finite settings, quote/currency/FX/quantity unit controls,
  continuous futures/historical sizing restrictions and cost-aware paper fills.
- Exchange schedules with proxy/coverage status, closed-bar filtering, freshness and historical
  universe receipts. Historical current RSS/event boosts are excluded or marked unavailable.
- Transactional SQLite journal/registry, visible legacy corruption, unique report workspaces,
  local experiment collection/settlement and matching-event comparisons.
- Runtime/source hashes, CLI structured file inputs, expanded regression and stdio tests,
  package validation, documentation and release/demo workflows.

Migration: legacy JSONL is imported once, transactionally, into journal.sqlite3. The original
is preserved; use journal_export for a current JSONL copy. Existing entries keep legacy
simple-return events. New full-desk records require prior/evidence/adjustments. Requires
Python 3.11+. Historical benchmark scores do not validate the changed event/fill models.

## 0.1.1 (2026-09-28)

Added
- Market swarm, `/tradefloor:swarm`. A seed analyst gathers the events; one persona agent
  per market participant group (India: foreign institutions, domestic funds, retail, prop
  desks, market makers, event funds; the US has its own roster) states its reaction as
  numbers; an agent-based simulation runs 2,000 traders over 1,000 Monte Carlo worlds,
  calibrated to the stock's own volatility, tails and drift, and reports the odds against
  normal behaviour, a fan of outcomes and who moved the price. `what-if "<event>"` reruns the
  personas with an injected event; afterwards any group can be questioned in character.
  Calls are journaled as source `swarm`. Inspired by MiroFish; no code shared.
- Two MCP tools, `swarm_roster` and `swarm_simulate`, also in the CLI (17 tools in all).
- `journal_review` breaks scores down by source (quant, full desk, swarm) when there is
  more than one.
- `server/scripts/eval_swarm.py` and the first calibration writeup,
  `benchmarks/results/2026-09-28-swarm-calibration.md`.

Changed
- The quant model's 80% range now uses max(EWMA, 1-year realised) volatility instead of
  the EWMA alone. On one-month outcomes of NIFTY 50 and S&P 500 stocks over the past year,
  its 80% ranges held 73% and 70% of outcomes before and 80% and 77% after.
  `direction`, `analyze` and `trade_plan` ranges are wider as a result.

## 0.1.0 (2026-09-28)

First public version.

- MCP server with 15 tools: symbol resolution for 41 exchanges and index names, technical
  report, calibrated direction forecast, fundamentals, localized news, sentiment signals,
  macro context, trade plan, watchlist scan, intraday scan (pre-market and live), journal
  record and review, settings. Also available as the `tradefloor` CLI.
- Two desks as agents: `analyze` (12 roles for one instrument) and `scout` (11 roles for a
  market, pre-market or live), with every role writing a file the next one reads.
- Journal grading: hit rate and Brier score against the base rate for swing calls; R
  multiples on 5-minute bars for intraday calls; big-move Brier score and a two-sided
  opening-range trade for pre-market picks.
- Point-in-time `as_of` and `at` replays, with no-look-ahead tests.
- Hosts: Claude Code, Codex, Antigravity; generated from one source by `tools/build.py`.
- Walk-forward evaluation script for the pre-market model.
- The MCP server starts with `python -m tradefloor.server`, so a running session on
  Windows cannot block a reinstall by locking a console-script executable.
