# Launch runbook

## Release verification

Record results for the release revision in [release-readiness.md](release-readiness.md).

1. Run generated-file checks, all offline tests and `uv build --project server`.
2. Install the built wheel in a clean environment; verify CLI/MCP and packaged demo assets.
3. Run the provider-dependent smoke script with isolated TRADEFLOOR_HOME. Missing data is
   a visible degraded result, never a substituted price or a passing claim.
4. Build `tradefloor-demo --export dist/demo/index.html`. Open it on desktop/mobile widths;
   exercise all three events, assumptions, fork, reveal, export and import. Verify a
   downloaded export with Python run_bundle. This needs a real browser.
5. Inspect the diff and release artifacts for secrets and licensed provider snapshots.
   Public demo artifacts must contain only synthetic fixtures.
6. Commit reviewed changes, publish the matching v0.3.0 tag and release artifacts. The
   pinned Antigravity configuration relies on that tag. These remote actions have not
   been performed by preparing this working tree.

## Public demo

The manual `demo-artifact.yml` workflow builds standalone HTML and uploads it as a GitHub
Actions artifact. Download it and host it on your preferred static site, or attach it to
a release. No server, keys or signup needed. Publishing a static synthetic file is the
supported public demo path; the loopback Python server is not a hosted service.

Alternatively, select **GitHub Actions** as the repository's Pages source and manually run
`pages.yml`. It tests and builds a synthetic-only static artifact, then deploys through
the `github-pages` environment. This workflow is prepared but has not been dispatched.
Verify the resulting public URL in a real browser before adding it to README or Show HN.

For the local workspace, also exercise project save/reopen, compare, counterexample jobs,
cancellation, evidence retraction/freeze, archive import/export and model arena. Consult
`workspace.md` for provider configuration, job recovery and the deployment boundary.

Add the actual live demo URL to README after verifying it. Keep the release wheel and
source tag available for users who want custom snapshots or arbitrary assumptions.

## Show HN draft

Title: **Show HN: Tradefloor — an open financial scenario lab that keeps its assumptions**

Suggested opening (adapt in your own voice):

> I built Tradefloor to turn market narratives into experiments I can inspect later.
> The demo uses fictional data: choose an event, challenge the reaction assumptions,
> compare baselines, reveal an outcome and export or fork the frozen run. No signup or
> API key. The Python CLI/MCP also supports market research and an experimental constrained
> order book. I have not demonstrated a trading edge. I'd especially like feedback on
> falsification, evaluation and how the assumptions should be tested.

Link the playable demo and source. Explain personal motivation and what you built;
avoid world-first/profitability claims, launch hype, or presenting agent personas as real
institutional flows. Be present to answer technical questions.

Before posting, verify the public demo, a clean installation from the published source,
and one actual research workflow in each AI host advertised in README. Check the pushed
revision's CI results. Share the project as an experimental research workspace and keep
the feature scope and validation limits visible. A GitHub push alone does not verify these.

[Show HN guidelines](https://news.ycombinator.com/showhn.html) favor things people can
try without barriers. The [current Show HN restriction notice](https://news.ycombinator.com/showlim)
also discusses participation eligibility; review it on launch day. Do not solicit votes.

## What cannot be completed by a code release

Prospective outcomes require elapsed time and externally timestamped commitments. Market
data rights require permission from rights holders. Exact venue exceptional sessions,
provider reliability and learned behavioral coefficients require empirical verification.
The roadmap distinguishes these from implemented research tooling.
