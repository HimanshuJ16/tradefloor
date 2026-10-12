# Release readiness

Release candidate: **0.5.0, 2026-10-12**. This is experimental, single-user local research
software with a synthetic-only public demo. It is not a validated trading system.

## Verified locally

| Check | Observed result |
|---|---|
| Offline Python suite | 233 passed, 2 upstream calendar deprecation warnings, 57.91 seconds |
| Frontend suites | 23 passed: classic UI, workspace calculations, research map and source/report escaping |
| Generated host files | All 80 match their sources |
| Python syntax/undefined-name lint | Passed |
| Distribution | 0.5.0 wheel and source archive built |
| Real packaged MCP protocol | 64 tools; scenario -> document -> search -> evidence branch -> cited report; zero provider calls |
| Public-document network canary | Real HTTPS documentation captured with original hash and extracted passages, in an isolated data home |
| Static artifact | 21 synthetic receipts; hashes, rights, lineage and exact packaged UI checked |

New source tests cover exact spans, duplicate identities, BM25 search, corrupted storage,
HTML script/form exclusion, PDF worker extraction and encrypted-PDF failures, date eligibility,
unchanged prices/assumptions in evidence branches, public-address/TLS connection pinning,
unsafe destinations, SEC metadata links and escaped reports that omit future settlement.

## Browser checks

Chrome verified fictional imports, HTML-to-text ingestion, passage search, source selection,
evidence freezing, saved-project reopen with the frozen passages intact, report preview,
and browser-downloaded Markdown/HTML containing the exact source appendix. A 390-pixel
report preview had no document-wide overflow. Static source inspection and report preview
worked; capture/import/freeze operations remained disabled there. No captured console errors.

Automated browser file selection was blocked by the ChatGPT extension's file-URL permission.
PDF extraction and the server import contract passed automated tests; normal manual file
selection does not require the ChatGPT extension. Print / Save as PDF uses the browser's
print dialog; a PDF file was not saved through that native dialog during automation.

Prior research-map QA covered live synthetic agent states, cancellation, recorded replay,
search, filters, keyboard/list selection, mobile layout and evidence withdrawal branches.
Model transport tests use synthetic SSE fixtures; they do not establish real model quality.

## Host and provider limits

Codex CLI 0.160.0 and Claude Code 2.1.284 were present. The packaged stdio MCP protocol was
exercised directly, not through a model-driven session in either host. Generated host
instructions and manifests match 0.5.0. Cloud model calls remain skipped by the owner's
choice. SEC live capture needs a configured application/contact; SEC discovery is fixture-tested.

Public prospective performance, source historical completeness/rights, model training
cutoffs, factual entailment and empirical behavioral/market-impact calibration remain unverified.
Screenshots contain only fictional fixtures: [cited report](../assets/qa/cited-report.jpg),
[mobile report](../assets/qa/cited-report-mobile.jpg), [research map](../assets/qa/research-map.jpg).

## Publication status

Implementation commit `bcb12d5` is pushed. GitHub CI passed all nine Ubuntu/Windows/macOS
Python 3.11/3.12/3.13 jobs and the package/MCP job:
[CI run](https://github.com/HimanshuJ16/tradefloor/actions/runs/38253623612).
The synthetic Pages workflow passed its tests/artifact gate and deployed:
[deployment](https://github.com/HimanshuJ16/tradefloor/actions/runs/38253690188).

**Public demo:** https://himanshuj16.github.io/tradefloor/

Real-browser public QA verified all three scenario switches, a precomputed assumption fork,
synthetic outcome reveal, source/report preview, browser HTML download and the interactive
map. Mobile thesis/report layouts had no document-wide overflow. No captured console errors.
[Public deployment screenshot](../assets/qa/public-demo.jpg).

The 0.5 tag/release is being finalized from the reviewed source. No Hacker News submission
has been made. Cloud provider calls and model-driven host sessions remain unverified, as
stated above; the public launch is an experimental synthetic research demonstration.

The only supported public hosting target is the standalone synthetic HTML. The loopback
workspace has no multi-user authentication or tenant isolation and remains local.
