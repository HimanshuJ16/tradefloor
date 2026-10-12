# Release readiness

Latest recorded verification: **0.4.0, 2026-10-12**. Update this document after rerunning
checks for the exact revision being released; these results do not certify later edits.

This is a verified local research release candidate and static-demo build. It is not a
verified public deployment or evidence of trading skill. No release tag, push, hosted
deployment or Hacker News post was made during this work.

The current full suite and repeatable release verifier ran on October 12. Live model calls
were explicitly skipped by the project owner. GitHub read-only inspection confirmed the
repository is public and Pages is not configured; no publishing action was performed.

## Automated checks

| Check | Observed result |
|---|---|
| Full offline Python suite | 215 passed on Windows / Python 3.14, 57.73 seconds |
| Frontend regression suites | 21 passed: 8 classic UI, 4 workspace calculation and 9 research-map tests |
| New workspace JavaScript syntax | Passed |
| Python undefined-name / syntax lint | Passed (`ruff check --select F,E9`) |
| Generated host files | All 80 match their sources |
| Distribution build | Wheel and source archive built for 0.4.0 |
| Isolated wheel installation | 61 tools and packaged workspace assets verified |
| Static artifact | 21 frozen synthetic receipts, validated hashes and semantic contracts |
| Repeatable release verifier | Local checks passed; source review/commit and Pages publication remain pending |
| Browser-downloaded project and receipt | Reimported and verified in an isolated data home |
| Claude Code plugin and marketplace | Generated 0.4 manifests match their sources; full model-driven host sessions remain unverified |

The earlier 0.2 validation recorded a live provider canary with 25 successful calls across
15 core tools. That historical result does not verify the new SEC/ALFRED adapters or current
provider availability; rerun the live checks for a release that advertises those functions.

The Python suite reports two upstream `exchange_calendars` NumPy timedelta deprecation
warnings. No failing tests were waived. The GitHub Actions OS/Python matrix is configured
but was not remotely executed in this session. An isolated wheel install proves packaging,
not correctness across every dependency resolution or supported operating system.

New regression coverage includes project revision conflicts and ancestor archives,
evidence retraction/freeze/fork, falsified graph edges/status, malformed hashed receipts,
timeline revisions and unknown availability, job cancellation/idempotency/lease recovery,
workspace HTTP jobs and archives, CLI success with a null error field, forecast event
alignment, moving-block evaluation, non-backdatable memory and numerical benchmarks.

## Real-browser checks

Research-map QA used an isolated data home and five synthetic roles, without cloud calls.
Chrome checks covered evidence selection, complete list and keyboard selection, search with
no matches, neighborhood focus, zoom, replay at the pre-response checkpoint, pause/latest,
and a real evidence-retraction child receipt. A slow synthetic stream showed working
roles and cancellation without automatic replay. Early-load preview controls wait for
connections and context to finish loading. A 390-pixel viewport had no document-wide
overflow. The saved images contain synthetic fixtures only. Static-map inspection remains
available while model calls and evidence branch creation stay disabled.

New 0.4 checks used an isolated data home and a loopback synthetic SSE endpoint. They
verify transport and UI behaviour, not the quality or availability of a real language model:

- Save two connection profiles, fixed-prompt connection test and independent comparison.
- Context/destination preview, streamed activity, tool receipts, claim audits, probability
  adjustment inspection, disagreement gaps and proposed observations.
- Follow-up preview on the same frozen source; saved session reopen and configuration recipes.
- Browser session export/import with canonical JSON preserved; audits recomputed, imported
  sessions marked untrusted and retained separately.
- Cancellation during a slow stream, partial output retained and usable controls restored.
- Daily CSV file selection/import, 900-row synthetic dataset and supplied-data scenario with
  no fabricated outcome reveal. Unit tests verify symbol/rights preservation through forks.
- Research desk at 390 pixels, connections/data hub at 320 pixels; no document-wide overflow.
- No captured console errors during the exercised new flows. Paid provider calls were not run.

The model-desk Python cases cover both SSE protocols, usage parsing, credential redaction and
OS-vault boundaries and failed credential rotation, endpoint restrictions, redirects/incomplete streams, preview hashing,
idempotency, no replay of interrupted paid calls, cancellation, forbidden model tools,
claim/quote/number checks, probability budgets, archive tampering and browser number formatting,
dated memory, CSV provenance, future commitments/matured supplied outcomes and HTTP-worker flow.

Additional launch regressions reject malformed response structures, malformed adjustments,
corrupted closed memory and score merging across different connections with the same alias.
The artifact verifier checks credential-field exclusion, modified distributions, complete
fixture coverage, source/UI consistency and fork lineage. Both static-demo workflows enforce it.

The following baseline browser workflows were previously checked for 0.3:

Executed in the ChatGPT in-app browser with synthetic examples. The original workflow
checks used an isolated data home; the terminal refresh was also checked on local port 8765:

- Project creation, custom assumption fork, save/reopen and branch comparison.
- Bounded counterexample search; progress display and cancellation back to usable controls.
- Assumption sensitivity ranking and four-model arena.
- Evidence copy, inspector, retraction, dependent review status and explicit child freeze.
- Full project archive download/import and current receipt download; server-side verification.
- Exact document comparison, supplied factor-shock arithmetic and empty information timeline.
- Standalone policy/crowded-exit switching, preset forks, outcome reveal and preset counterexample.
- Desktop and 390/320-pixel mobile layouts. No document-wide horizontal overflow at 320;
  the workspace view navigation intentionally scrolls horizontally.
- Mobile project controls expand/collapse. No captured console errors in either workspace
  or standalone demo during the exercised flows.
- Terminal refresh: scenario cards, return/price chart units, saved-day keyboard inspection,
  computed thesis summary, and searchable command menu with Enter selection and Escape dismissal.

The workspace calculation tests cover price conversion, saved-observation selection,
probability-point shifts, evidence review counts and the log-return event band. They do not
replace browser interaction checks or certify accessibility conformance.

The mobile view now opens on the research result, with assumptions behind an explicit
toggle. Job progress/cancel controls remain above the view navigation. Custom loaded runs
retain their actual assumptions; evidence edits create new receipts. Full archives retain
canonical run strings so the browser does not change hash-significant numeric encodings.

Screenshots: [research map](../assets/qa/research-map.jpg), [mobile research map](../assets/qa/research-map-mobile.jpg),
[research desk](../assets/qa/research-desk.jpg), [desktop workspace](../assets/workspace-preview.jpg),
[mobile standalone](../assets/qa/workspace-v03-mobile.jpg). These are real browser captures
of synthetic examples. They are not design mockups or market performance demonstrations.

## Artifacts and launch boundary

Local build outputs are in `dist/`: `tradefloor-0.4.0-py3-none-any.whl`,
`tradefloor-0.4.0.tar.gz`, `demo/index.html` and `SHA256SUMS-v0.4.0.txt`.
The machine-readable verification report is `dist/launch-check-v0.4.0.json`.
Build outputs are intentionally ignored by Git. The Pages workflow can build and deploy
the synthetic artifact after repository configuration and a reviewed revision.

Still required for a public launch: publish the reviewed source/release, configure Pages,
deploy, verify its actual public URL and then prepare the final Show HN submission. The
loopback research server is not suitable for Internet exposure as a multi-user service.

SEC/ALFRED tests use controlled fixtures; configured live canaries were not run. Public
prospective commitments, matured outcomes, licensed historical completeness, external
model training cutoffs and empirical microstructure calibration remain unverified.
See the [implementation roadmap](../ROADMAP.md),
[workspace contracts](workspace.md) and [launch runbook](launch-runbook.md).
