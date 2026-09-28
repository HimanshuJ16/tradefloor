"""Market swarm: an agent-based simulation of the crowd around one instrument.

A population of simulated traders, split into participant groups (foreign institutions,
domestic funds, retail, prop desks, market makers, event traders, ...), trades every day of
the horizon. Each trader mixes four behaviours with individual strengths:

  fundamental  pulls toward the group's fair-value belief
  trend        buys what has risen over the last week, sells what has fallen
  contrarian   the opposite (a negative trend weight)
  news         pushes in the direction of the group's reaction to the seed events,
               fading with the group's persistence

Net demand moves the price; a fat-tailed noise term stands for everything unmodelled. The
noise is calibrated so the baseline (no news reaction) reproduces the stock's own recent
volatility, its tail thickness, and its normal drift. Group reactions (sentiment,
conviction, persistence, fair-value shift) come from LLM persona agents or from a user's
what-if; the simulation turns them into a distribution of outcomes, a fan of paths, and an
attribution of who moved the price.

The simulation does not know the future. It answers: given how this stock normally moves,
and given these reactions, what spread of outcomes follows? Whether the reactions add skill
is measured by the journal (source "swarm") against the plain quant model.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from . import indicators as ind

TREND_WINDOW = 5
KAPPA_F = 0.02      # daily pull toward fair value per unit of log gap, in sigma units
NEWS_BETA = 0.5     # a unanimous, fully convinced reaction pushes about 0.5 sigma on day one
IMPACT = 1.0        # sigma of return per unit of net demand
FLAT_BAND_SIGMA = 0.25


@dataclass(frozen=True)
class Group:
    id: str
    name: str
    weight: float
    k_fundamental: float
    k_trend: float
    k_news: float
    participation: float
    description: str


# Default rosters. The weights are illustrative shares of trading influence, not measured
# data; pass `weights` to override them.
ROSTERS: dict[str, list[Group]] = {
    "in": [
        Group("fii", "Foreign institutional investors", 0.18, 0.5, 0.3, 1.0, 0.6, "Global funds; move on the dollar, US yields, crude, country allocation and earnings revisions."),
        Group("dii", "Domestic mutual funds and insurers", 0.17, 1.0, -0.2, 0.5, 0.7, "Steady SIP inflows; buy dips in quality, slow to react, valuation-anchored."),
        Group("retail", "Retail traders", 0.30, 0.1, 0.8, 1.2, 0.5, "Momentum and headline driven; crowd into trending names, react fast to news and social media."),
        Group("prop", "Proprietary and algorithmic desks", 0.20, 0.0, 0.5, 0.8, 0.9, "Short horizon; trade intraday momentum and news flow, flat by the close."),
        Group("mm", "Market makers and option writers", 0.10, 0.0, -0.6, 0.2, 0.9, "Provide liquidity, hedge options books, lean against short-term moves."),
        Group("event", "Event and special-situation funds", 0.05, 0.6, 0.0, 1.5, 0.4, "Trade specific catalysts: results, mergers, index changes, regulatory decisions."),
    ],
    "us": [
        Group("inst", "Long-only institutions", 0.30, 1.0, -0.1, 0.5, 0.6, "Pensions and mutual funds; valuation and earnings driven, slow to move."),
        Group("retail", "Retail traders", 0.20, 0.1, 0.8, 1.2, 0.5, "Momentum, options and headline driven; fast reactions."),
        Group("cta", "Trend followers and quant funds", 0.15, 0.0, 1.0, 0.2, 0.8, "Systematic; follow price trends and volatility signals."),
        Group("hf", "Hedge funds and event funds", 0.15, 0.6, 0.2, 1.3, 0.6, "Trade catalysts, earnings, macro and relative value."),
        Group("mm", "Market makers and option dealers", 0.15, 0.0, -0.6, 0.2, 0.9, "Provide liquidity, hedge dealer gamma, lean against short-term moves."),
        Group("passive", "Index and passive flows", 0.05, 0.0, 0.0, 0.0, 1.0, "Mechanical flows; no view."),
    ],
}
ROSTERS["default"] = ROSTERS["us"]
REGION_OF_EXCHANGE = {"NSE": "in", "BSE": "in", "US": "us", "FUT": "us", "CRYPTO": "us"}


def roster(exchange_code: str, weights: dict[str, float] | None = None) -> list[Group]:
    groups = ROSTERS.get(REGION_OF_EXCHANGE.get(exchange_code, "default"), ROSTERS["default"])
    if weights:
        groups = [Group(**{**asdict(g), "weight": float(weights.get(g.id, g.weight))}) for g in groups]
    total = sum(g.weight for g in groups) or 1.0
    return [Group(**{**asdict(g), "weight": g.weight / total}) for g in groups]


@dataclass
class Reaction:
    group: str
    sentiment: float = 0.0         # -1 very bearish .. +1 very bullish
    conviction: float = 0.5        # 0 split crowd .. 1 unanimous
    persistence_days: float = 5.0  # half-life of the reaction
    fair_value_shift_pct: float = 0.0

    @staticmethod
    def parse(d: dict) -> "Reaction":
        clip = lambda v, lo, hi, dflt: float(min(hi, max(lo, float(d.get(v, dflt) if d.get(v) is not None else dflt))))  # noqa: E731
        return Reaction(group=str(d["group"]), sentiment=clip("sentiment", -1, 1, 0), conviction=clip("conviction", 0, 1, 0.5),
                        persistence_days=clip("persistence_days", 0.5, 60, 5), fair_value_shift_pct=clip("fair_value_shift_pct", -50, 50, 0))


def stock_profile(df: pd.DataFrame, horizon_days: int) -> dict:
    """What the simulation must reproduce: daily vol, tail thickness, and normal drift."""
    lr = ind.log_returns(df["Close"]).dropna()
    # Never assume the next weeks are calmer than the past year: on 2025-26 NIFTY and S&P
    # stocks, the current (EWMA) volatility alone gave 80% ranges that held 69-73% of outcomes.
    sigma_d = max(float(ind.ewma_vol_daily(df["Close"]).iloc[-1]), float(lr.tail(252).std()))
    recent = lr.tail(252)
    kurt = float(recent.kurt()) if len(recent) > 30 else 3.0
    df_t = float(np.clip(4 + 6 / max(kurt, 0.1), 3.0, 30.0))  # Student-t with this excess kurtosis
    hist = (np.log(df["Close"]).shift(-horizon_days) - np.log(df["Close"])).dropna()
    mu_h = float(hist.median()) if len(hist) > 60 else 0.0  # same full history as the quant model's base rates
    return {"sigma_d": sigma_d, "df_t": df_t, "mu_daily": mu_h / max(horizon_days, 1), "price": float(df["Close"].iloc[-1])}


def _t_noise(rng: np.random.Generator, shape, df_t: float) -> np.ndarray:
    z = rng.standard_t(df_t, size=shape)
    return z / math.sqrt(df_t / (df_t - 2)) if df_t > 2 else z


def _simulate(profile: dict, groups: list[Group], reactions: dict[str, Reaction], horizon: int, runs: int,
              agents: int, noise: float, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    sig, mu = profile["sigma_d"], profile["mu_daily"]
    x = np.zeros(runs)                                   # log price relative to today
    hist = np.zeros((runs, TREND_WINDOW))                # last daily returns, for the trend signal
    paths = np.zeros((runs, horizon))
    contrib = {g.id: np.zeros(runs) for g in groups}
    pop = []
    for g in groups:
        n = max(1, int(round(agents * g.weight)))
        r = reactions.get(g.id, Reaction(g.id))
        k = lambda base: base * rng.lognormal(0.0, 0.3, n)  # noqa: E731 individual strength
        disp = (1.0 - r.conviction) * 0.6                  # a split crowd disagrees more
        s_i = np.clip(r.sentiment + rng.normal(0.0, disp, n), -1, 1)
        pop.append((g, n, k(g.k_fundamental), k(g.k_trend), k(g.k_news), s_i, r))
    for t in range(horizon):
        trend_z = hist.sum(axis=1) / (sig * math.sqrt(TREND_WINDOW))
        demand_total = np.zeros(runs)
        for g, n, kf, kt, kn, s_i, r in pop:
            active = rng.random((runs, n)) < g.participation
            gap = math.log(1 + r.fair_value_shift_pct / 100) - x          # log(F / p)
            fundamental = kf[None, :] * (KAPPA_F * gap[:, None] / sig)
            trend = kt[None, :] * 0.1 * trend_z[:, None]
            news = kn[None, :] * s_i[None, :] * NEWS_BETA * (0.5 ** (t / r.persistence_days))
            d = ((fundamental + trend + news) * active).mean(axis=1) * g.weight
            contrib[g.id] += IMPACT * d * sig
            demand_total += d
        ret = mu + sig * (IMPACT * demand_total + noise * _t_noise(rng, runs, profile["df_t"]))
        x = x + ret
        hist = np.roll(hist, -1, axis=1)
        hist[:, -1] = ret
        paths[:, t] = x
    return {"final": x, "paths": paths, "contrib": contrib}


def calibrate_noise(profile: dict, groups: list[Group], horizon: int, agents: int, seed: int) -> float:
    """Scale the noise so the baseline's spread over the whole horizon matches the stock's
    (sigma x sqrt(horizon)). Matching daily volatility is not enough: market makers,
    contrarians and the fair-value pull add mean reversion, which narrows the horizon spread
    even when each day's spread is right."""
    noise = 1.0
    target = profile["sigma_d"] * math.sqrt(horizon)
    for _ in range(4):
        sim = _simulate(profile, groups, {}, horizon, 400, agents, noise, seed)
        spread = float((sim["final"] - profile["mu_daily"] * horizon).std())
        if spread <= 0:
            break
        noise *= target / spread
    return noise


def _summary(sim: dict, profile: dict, horizon: int) -> dict:
    fin = sim["final"]
    band = FLAT_BAND_SIGMA * profile["sigma_d"] * math.sqrt(horizon)
    q = lambda p: float(np.expm1(np.quantile(fin, p)) * 100)  # noqa: E731
    fan_days = sorted({max(1, horizon // 4), max(1, horizon // 2), max(1, 3 * horizon // 4), horizon})
    return {
        "p_up": round(float((fin > band).mean()), 3), "p_down": round(float((fin < -band).mean()), 3),
        "p_flat": round(float((np.abs(fin) <= band).mean()), 3),
        "return_pct": {"p10": round(q(0.1), 2), "p50": round(q(0.5), 2), "p90": round(q(0.9), 2)},
        "price": {"p10": round(profile["price"] * math.exp(np.quantile(fin, 0.1)), 4),
                  "p50": round(profile["price"] * math.exp(np.quantile(fin, 0.5)), 4),
                  "p90": round(profile["price"] * math.exp(np.quantile(fin, 0.9)), 4)},
        "fan": [{"day": d, "p10": round(float(np.expm1(np.quantile(sim["paths"][:, d - 1], 0.1)) * 100), 2),
                 "p50": round(float(np.expm1(np.quantile(sim["paths"][:, d - 1], 0.5)) * 100), 2),
                 "p90": round(float(np.expm1(np.quantile(sim["paths"][:, d - 1], 0.9)) * 100), 2)} for d in fan_days],
    }


def run(df: pd.DataFrame, exchange_code: str, horizon: int, reactions: list[dict] | None = None, runs: int = 1000,
        agents: int = 2000, seed: int = 7, weights: dict[str, float] | None = None) -> dict:
    profile = stock_profile(df, horizon)
    groups = roster(exchange_code, weights)
    noise = calibrate_noise(profile, groups, horizon, agents, seed)
    base = _simulate(profile, groups, {}, horizon, runs, agents, noise, seed)
    out = {
        "agents": agents, "worlds": runs, "horizon_trading_days": horizon,
        "groups": [{"id": g.id, "name": g.name, "weight": round(g.weight, 3)} for g in groups],
        "calibration": {"daily_vol_pct": round(profile["sigma_d"] * 100, 3), "tail_df": round(profile["df_t"], 1),
                        "normal_drift_pct_per_day": round(profile["mu_daily"] * 100, 4), "noise_scale": round(noise, 3)},
        "baseline": _summary(base, profile, horizon),
        "assumptions": {"news_push_sigma_day1_if_unanimous": NEWS_BETA, "fair_value_pull_per_day": KAPPA_F,
                        "trend_window_days": TREND_WINDOW, "group_weights": "illustrative defaults, not measured shares"},
    }
    if reactions:
        parsed = {r.group: r for r in (Reaction.parse(d) for d in reactions)}
        unknown = sorted(set(parsed) - {g.id for g in groups})
        scen = _simulate(profile, groups, parsed, horizon, runs, agents, noise, seed)  # same seed: common random numbers
        s = _summary(scen, profile, horizon)
        out["scenario"] = s
        out["reactions"] = [asdict(r) for r in parsed.values()]
        out["shift"] = {"p_up": round(s["p_up"] - out["baseline"]["p_up"], 3), "p_down": round(s["p_down"] - out["baseline"]["p_down"], 3),
                        "median_return_pct": round(s["return_pct"]["p50"] - out["baseline"]["return_pct"]["p50"], 2)}
        attr = [{"group": g.id, "name": g.name,
                 "moved_price_pct": round(float((scen["contrib"][g.id] - base["contrib"][g.id]).mean()) * 100, 2)} for g in groups]
        out["who_moved_the_price"] = sorted(attr, key=lambda a: -abs(a["moved_price_pct"]))
        if unknown:
            out["warning"] = f"Reactions for unknown groups ignored: {unknown}"
    return out
