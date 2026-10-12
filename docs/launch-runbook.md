# Launch runbook

## Release verification

Record results for the release revision in [release-readiness.md](release-readiness.md).

After building the wheel/source archive, exporting the demo and refreshing their checksum
manifest, run the repeatable verification command:

```bash
uv run --locked --project server --group dev python tools/verify_launch.py --tests --skip-live --github HimanshuJ16/tradefloor --output dist/launch-check-v0.5.0.json
```

The report separates local checks from an uncommitted source revision, unconfigured Pages,
skipped live calls and pending public browser QA. It never publishes, changes Pages settings
or makes model requests. `--skip-live` records an intentional skip, not successful live validation.
The public demo may be launched as a synthetic research demonstration with that limit stated.
Both demo workflows now verify all 21 hashes, case labels, unique run identities, fork lineage,
synthetic data rights, absence of credential fields, current engine identity and exact packaged
UI before uploading or deploying. A stale export fails instead of silently shipping old assets.

1. Run generated-file checks, all offline tests and `uv build --project server`.
2. Install the built wheel in a clean environment; verify CLI/MCP and packaged demo assets.
3. Run the provider-dependent smoke script with isolated TRADEFLOOR_HOME. Missing data is
   a visible degraded result, never a substituted price or a passing claim.
4. Build `tradefloor-demo --export dist/demo/index.html`. Open it on desktop/mobile widths;
   exercise all three events, assumptions, fork, reveal, export and import. Verify a
   downloaded export with Python run_bundle. This needs a real browser.
5. Inspect the diff and release artifacts for secrets and licensed provider snapshots.
   Public demo artifacts must contain only synthetic fixtures.
6. Commit reviewed changes, publish the matching v0.5.0 tag and release artifacts. The
   pinned Antigravity configuration relies on that tag. The 0.5 release is being finalized after the verified Pages deployment.

## Public demo

The manual `demo-artifact.yml` workflow builds standalone HTML and uploads it as a GitHub
Actions artifact. Download it and host it on your preferred static site, or attach it to
a release. No server, keys or signup needed. Publishing a static synthetic file is the
supported public demo path; the loopback Python server is not a hosted service.

Alternatively, select **GitHub Actions** as the repository's Pages source and manually run
`pages.yml`. It tests and builds a synthetic-only static artifact, then deploys through
the `github-pages` environment. The 0.5 workflow has been dispatched and its public URL verified.
Verify the resulting public URL in a real browser before adding it to README or Show HN.

For the local workspace, also exercise project save/reopen, compare, counterexample jobs,
cancellation, evidence retraction/freeze, archive import/export and model arena. Consult
`workspace.md` for provider configuration, job recovery and the deployment boundary.

Add the actual live demo URL to README after verifying it. Keep the release wheel and
source tag available for users who want custom snapshots or arbitrary assumptions.

## Verified public demo and Show HN draft

Live demo: **https://himanshuj16.github.io/tradefloor/**
Source: **https://github.com/HimanshuJ16/tradefloor**
Release target: **https://github.com/HimanshuJ16/tradefloor/releases/tag/v0.5.0**

Public browser QA covered scenario switching, assumption forks, outcome reveal, map
inspection, source/report preview and HTML export on desktop/mobile. The Pages build
checks the synthetic-only receipts before deployment. Publish only this static artifact.

Submission title (review before posting):

**Show HN: Tradefloor - a local financial research desk with inspectable evidence**

Submission URL:

**https://himanshuj16.github.io/tradefloor/**

Suggested first comment; edit the personal motivation to match your experience:

> I built Tradefloor to make market narratives inspectable: what assumptions drive a
> conclusion, which sources support it, and what would change the thesis?
>
> The demo runs entirely in the browser on fictional data, without signup or API keys.
> You can choose an event, change reaction assumptions, compare numerical baselines,
> inspect evidence connections, reveal a synthetic outcome and export a cited report.
>
> Locally, the Python CLI/MCP and workspace add persistent projects, text/HTML/PDF sources,
> exact passage search, explicit source capture, user-selected model roles, recorded replay,
> probability/reference audits and supplied-outcome scoring. Sources are reviewed and frozen
> before model calls. The map shows recorded relationships, not private model reasoning.
>
> This is experimental research software. I have not demonstrated a trading edge. The
> agents' judgments and source dates still require review. Cloud-provider canaries and full
> model-driven host sessions were not run for this release; the packaged MCP workflow,
> offline tests and public demo were verified. Broker execution is out of scope.
>
> Source: https://github.com/HimanshuJ16/tradefloor
> I'd like feedback on the evidence workflow, scenario falsification and evaluation design.

The draft is prepared; it has not been submitted. Review it in your own voice and remain
available to discuss the design and limitations. Don't solicit votes. The
[Show HN guidelines](https://news.ycombinator.com/showhn.html) favor projects users can try
without barriers, and allow early-stage work. Check the
[current participation restriction notice](https://news.ycombinator.com/showlim) before posting.

## What cannot be completed by a code release

Prospective outcomes require elapsed time and externally timestamped commitments. Market
data rights require permission from rights holders. Exact venue exceptional sessions,
provider reliability and learned behavioral coefficients require empirical verification.
The roadmap distinguishes these from implemented research tooling.
