"""User settings, layered so every agent host can configure tradefloor.

Precedence, highest first:
1. Environment variables (TRADEFLOOR_*). Hosts with a settings UI (Claude Code userConfig,
   Gemini CLI extension settings) pass values this way.
2. ~/.tradefloor/config.json (or $TRADEFLOOR_HOME/config.json), written by the `settings`
   tool. Hosts without a settings UI configure here, once, for every host.
3. Defaults below.

A value still containing "${" is a placeholder the host did not expand. It is treated as
unset rather than trusted, because hosts differ in which variables they substitute.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import markets

# key -> (env var, type, default, description)
SPEC: dict[str, tuple[str, type, object, str]] = {
    "default_market": ("TRADEFLOOR_DEFAULT_MARKET", str, "US", "Exchange code for bare tickers, e.g. US, NSE, LSE, TSE"),
    "default_horizon": ("TRADEFLOOR_DEFAULT_HORIZON", str, "1m", "Horizon when none is given: 1w, 2w, 1m, 3m, 6m, 1y"),
    "capital": ("TRADEFLOOR_CAPITAL", float, 0.0, "Capital for position sizing in your home currency; 0 skips sizing"),
    "risk_per_trade_pct": ("TRADEFLOOR_RISK_PCT", float, 1.0, "Percent of capital lost if the stop is hit"),
    "max_position_pct": ("TRADEFLOOR_MAX_POSITION_PCT", float, 20.0, "Cap on one position as percent of capital"),
    "intraday_risk_pct": ("TRADEFLOOR_INTRADAY_RISK_PCT", float, 0.5, "Percent of capital lost if an intraday stop is hit"),
    "debate_rounds": ("TRADEFLOOR_DEBATE_ROUNDS", int, 1, "Bull/bear debate rounds on a standard run (1 to 3)"),
}

BOUNDS = {"capital": (0, None), "risk_per_trade_pct": (0.1, 5), "intraday_risk_pct": (0.05, 3), "max_position_pct": (1, 100), "debate_rounds": (1, 3)}


def home() -> Path:
    raw = os.environ.get("TRADEFLOOR_HOME", "")
    p = Path(raw) if raw and "${" not in raw else Path.home() / ".tradefloor"
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    return home() / "config.json"


def _read_file() -> dict:
    try:
        return json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _coerce(key: str, value) -> object:
    _, typ, _, _ = SPEC[key]
    if typ is str:
        v = str(value).strip()
        if key == "default_market":
            v = v.upper()
            if v not in markets.EXCHANGES:
                raise ValueError(f"unknown market {v!r}; see list_markets")
        if key == "default_horizon":
            markets.horizon_to_days(v)  # raises on nonsense
        return v
    v = typ(float(value)) if typ is int else typ(value)
    lo, hi = BOUNDS.get(key, (None, None))
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise ValueError(f"{key} must be between {lo} and {hi}")
    return v


def _usable(raw) -> bool:
    return raw is not None and str(raw).strip() != "" and "${" not in str(raw)


def effective() -> dict:
    """Every setting with its value and where the value came from."""
    file = _read_file()
    out = {}
    for key, (env, _, default, desc) in SPEC.items():
        value, source = default, "default"
        if _usable(file.get(key)):
            try:
                value, source = _coerce(key, file[key]), "config.json"
            except (TypeError, ValueError):
                pass
        raw = os.environ.get(env)
        if _usable(raw):
            try:
                value, source = _coerce(key, raw), f"env {env}"
            except (TypeError, ValueError):
                pass
        out[key] = {"value": value, "source": source, "description": desc}
    return out


def get(key: str):
    return effective()[key]["value"]


def set_value(key: str, value) -> dict:
    if key not in SPEC:
        raise KeyError(f"unknown setting {key!r}; known: {', '.join(SPEC)}")
    v = _coerce(key, value)
    file = _read_file()
    file[key] = v
    config_path().write_text(json.dumps(file, indent=2), encoding="utf-8")
    eff = effective()[key]
    res = {"key": key, "saved": v, "path": str(config_path()), "effective": eff}
    if eff["source"].startswith("env"):
        res["note"] = (f"Saved, but {SPEC[key][0]} is set by your agent host and takes precedence. "
                       "Change it in the host's plugin settings instead (Claude Code: /config).")
    return res
