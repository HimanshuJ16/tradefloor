"""Public research contracts shared by the CLI, MCP and local workspace."""

from __future__ import annotations
from functools import wraps
from . import advanced, arena, evidence, intelligence, jobs, research, timeline

TOOLS = {}


def tool(fn):
    @wraps(fn)
    def safe(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            return {"error": str(exc)}

    TOOLS[fn.__name__] = safe
    return safe


@tool
def research_project(
    action: str = "list", project_id: str | None = None, body: dict | None = None
) -> dict:
    """Create/get/list/update/attach/history a local project; mutations require current revision."""
    return research.project(action, project_id, body)


@tool
def project_bundle(
    project_id: str | None = None,
    payload: dict | None = None,
    include_data: bool = False,
) -> dict:
    """Export a summary or explicitly include private source data; import complete projects."""
    if (project_id is None) == (payload is None):
        raise ValueError("provide project_id or payload")
    return (
        research.import_project(payload)
        if payload is not None
        else research.export_project(project_id, include_data)
    )


@tool
def project_scenario(project_id: str, run_id: str) -> dict:
    """Freeze edited project evidence/claims into a child scenario on unchanged numerical assumptions."""
    return research.project_scenario(project_id, run_id)


@tool
def compare_runs(run_ids: list[str]) -> dict:
    """Compare two to four branches with identical frozen prices and event contracts."""
    return research.compare(run_ids)


@tool
def thesis_challenge(
    run_id: str, bounds: dict | None = None, points: int = 3, budget: int = 40
) -> dict:
    """Find a nearest reversing point on a bounded finite assumption grid."""
    return research.challenge(run_id, bounds, points, budget)


@tool
def research_priority(run_id: str) -> dict:
    """Rank assumption endpoint sensitivity; not expected value of information."""
    return research.investigate(run_id)


@tool
def forecast_arena(
    run_id: str, seed: int = 7, draws: int = 2000, external: list[dict] | None = None
) -> dict:
    """Compare quant, bootstrap, EWMA, Student-t and optional supplied adapter forecasts."""
    return arena.forecast_run(run_id, seed, draws, external)


@tool
def robust_evaluation(
    cases: list[dict],
    block_length: int = 5,
    bootstrap_draws: int = 1000,
    seed: int = 7,
    trials: int = 1,
) -> dict:
    """Paired moving-block loss intervals and all-class reliability; promotion requires review."""
    return arena.evaluate(cases, block_length, bootstrap_draws, seed, trials)


@tool
def information_timeline(
    cutoff: str, series: str | None = None, records: list[dict] | None = None
) -> dict:
    """Append immutable supplied vintages, then select records eligible at cutoff."""
    if records is not None:
        timeline.ingest(records)
    return timeline.query(cutoff, series)


@tool
def archival_fetch(provider: str, identifier: str, vintage: str | None = None) -> dict:
    """Fetch SEC CIK submissions metadata or ALFRED series vintage with optional environment credentials."""
    return timeline.fetch(provider, identifier, vintage)


@tool
def document_changes(before: str, after: str) -> dict:
    """Compare bounded documents with exact character spans and content hashes."""
    return evidence.document_diff(before, after)


@tool
def research_record(kind: str, payload: dict) -> dict:
    """Append assessment/outcome/protocol/witness/proposal with explicit verification status."""
    return intelligence.append(kind, payload)


@tool
def research_memory(cutoff: str, context: str | None = None) -> dict:
    """Retrieve only assessments and outcomes known and recorded by cutoff."""
    return intelligence.memory(cutoff, context)


@tool
def research_job(
    action: str = "list",
    job_id: str | None = None,
    kind: str | None = None,
    arguments: dict | None = None,
    idempotency_key: str | None = None,
) -> dict:
    """Submit/list/get/cancel jobs. The demo owns a worker; CLI action work processes one queued job."""
    if action == "submit":
        return jobs.submit(kind, arguments or {}, idempotency_key)
    if action == "cancel":
        return jobs.cancel(job_id)
    if action == "work":
        jobs.Worker().once()
        return jobs.get(job_id)
    if action not in ("get", "list"):
        raise ValueError("unsupported job action")
    return jobs.get(job_id if action == "get" else None)


@tool
def factor_stress(holdings: list[dict], shocks: dict, account_currency: str) -> dict:
    """Transmit common shocks through explicit holdings factor loadings."""
    return advanced.factor_stress(holdings, shocks, account_currency)


@tool
def portfolio_allocate(
    covariance: list[list[float]], max_weight: float = 0.5, iterations: int = 2000
) -> dict:
    """Long-only minimum-variance allocation with capped weights and convergence diagnostics."""
    return advanced.allocate(covariance, max_weight, iterations)


@tool
def option_implied(
    spot: float,
    volatility: float,
    years: float,
    quote_as_of: str,
    rate: float = 0,
    dividend_yield: float = 0,
    flat_band: float = 0.02,
) -> dict:
    """Risk-neutral constant-volatility benchmark; distinct from physical forecasts and fitted surfaces."""
    return advanced.option_implied(
        spot, volatility, years, rate, dividend_yield, flat_band, quote_as_of
    )


@tool
def market_diagnostics(tape: list[dict], measured: list[dict] | None = None) -> dict:
    """Compare synthetic and supplied measured tape volatility/spreads without calibration claims."""
    return advanced.microstructure_diagnostics(tape, measured)


def register(mcp):
    for fn in TOOLS.values():
        mcp.tool()(fn)
