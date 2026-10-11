# Release readiness

Latest recorded verification: **0.3.0, 2026-10-11**. Update this document after rerunning
checks for the exact revision being released; these results do not certify later edits.

This is a verified local research release candidate and static-demo build. It is not a
verified public deployment or evidence of trading skill. No release tag, push, hosted
deployment or Hacker News post was made during this work.

## Automated checks

| Check | Observed result |
|---|---|
| Full offline Python suite | 171 passed on Windows / Python 3.14, 19.34 seconds |
| Frontend regression suites | 12 passed: 8 classic UI tests and 4 workspace calculation tests |
| New workspace JavaScript syntax | Passed |
| Python undefined-name / syntax lint | Passed (`ruff check --select F,E9`) |
| Generated host files | All 80 match their sources |
| Distribution build | Wheel and source archive built for 0.3.0 |
| Isolated wheel installation | 54 tools and packaged workspace assets verified |
| Static artifact | 21 frozen synthetic receipts, validated hashes and semantic contracts |
| Browser-downloaded project and receipt | Reimported and verified in an isolated data home |
| Claude Code plugin and marketplace | Local manifest validation passed; full model-driven sessions remain unverified for 0.3 |

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

Screenshots: [desktop workspace](../assets/workspace-preview.jpg),
[mobile standalone](../assets/qa/workspace-v03-mobile.jpg). These are real browser captures
of synthetic examples. They are not design mockups or market performance demonstrations.

## Artifacts and launch boundary

Local build outputs are in `dist/`: `tradefloor-0.3.0-py3-none-any.whl`,
`tradefloor-0.3.0.tar.gz`, `demo/index.html` and `SHA256SUMS-v0.3.0.txt`.
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
