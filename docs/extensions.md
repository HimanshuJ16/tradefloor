# Extension contracts

Tradefloor's extension boundary is versioned data. The workspace does not install or execute
arbitrary model packages from a receipt, URL, research proposal or uploaded file.

## Forecast adapter v1

Run a chosen model in its own environment and submit its output to `forecast_arena(external=[...])`:

```json
{
  "schema": "tradefloor-forecast-v1",
  "model_id": "my-model",
  "model_version": "checkpoint-and-adapter-version",
  "event_contract": {"copy": "the exact event_contract from the frozen source run"},
  "probabilities": {"up": 0.4, "down": 0.4, "flat": 0.2},
  "latency_ms": 1200,
  "cost_usd": null,
  "provenance": {
    "source_run_id": "copy-the-real-run-id",
    "source_sha256": "copy-the-real-receipt-hash",
    "model_checkpoint": "exact checkpoint identifier",
    "training_cutoff": "unknown unless established",
    "conversion_method": "document how predictions become event probabilities"
  }
}
```

The event placeholder above must be replaced by the complete real contract. The numerical
probabilities shown are schema examples, not financial predictions. The supplied model must
use the same frozen input history and cutoff. Validation checks the contract, probabilities,
costs and provenance shape; it cannot certify what an external program actually trained on.

Qlib/RD-Agent research workers and TimesFM/Chronos environments can submit through this
boundary. Native integrations and checkpoint downloads are **not bundled or verified** in
0.3. Each requires independent dependency, data-rights and model-quality evaluation.

## Data adapter v1

Submit records through `information_timeline(records=..., cutoff=...)`. Required fields:
`series`, `observation_key`, `source`, `rights`, `value`, `effective_at`, `retrieved_at`.
`published_at` and `available_at` may be null, but unknown availability is excluded from a
historical query. Include `availability_status`, vintage and source identifiers. Currency,
units and adjustment conventions belong in each value's documented schema.

An OpenBB-backed adapter can produce these records, but fetching current data does not
establish historical availability. The built-in SEC and ALFRED connectors are examples of
bounded first-party adapters. Their limitations are documented in [workspace.md](workspace.md).

## Simulation and report interchange

Scenario engines should retain exact event definitions, frozen history, seed, model version,
assumption ranges and conservation checks where relevant. External LEAN/Nautilus/ABIDES/
JAX-LOB outputs are not silently accepted as the built-in behavioral model's receipts.
Use independent forecast receipts or measured tape diagnostics until a versioned engine
adapter and conformance tests exist. QuantLib/Riskfolio are possible future optional engines;
0.3's pricing/portfolio functions are bounded native baselines, not wrappers around them.

Reports are data-only UTF-8 Markdown/JSON/text, frozen by `run_finalize`. Preserve original
claims and evidence alongside revisions. Never load an executable hook from a public report.

## Contribution gates

An adapter contribution needs synthetic fixtures for missing data, time cutoffs, source
revision, units, rate-limit failure and numerical/event-contract invariants. Document the
upstream version, code/model/data licenses, credentials and optional install instructions.
Passing a fixture test does not validate a provider's historical completeness or trading edge.

Schema changes need a version and a migration policy. Existing hashed receipts must remain
unchanged; create derived receipts with parent links rather than modifying old content.
