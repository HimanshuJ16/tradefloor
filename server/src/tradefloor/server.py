"""tradefloor MCP server. stdio transport; works with any MCP host.

Every tool returns a JSON object. Failures come back as {"error": ...} so an agent can
report the gap instead of filling it in.
"""

from __future__ import annotations

from datetime import date, datetime

from mcp.server.mcpserver import MCPServer

from . import calendars, data, evaluation, events, forecast, indicators, intraday, journal, lab, markets, microstructure, plan, portfolio, premarket, registry, runs, scout, settings, snapshots, swarm, validation

mcp = MCPServer(
    "tradefloor",
    instructions=(
        "tradefloor: market data and deterministic analytics for any exchange Yahoo Finance covers.\n"
        "Asked which way a stock, index, future, FX pair or crypto asset is heading, or for a quick "
        "view on one: call quick_direction(query, horizon) FIRST and answer from its result. It "
        "resolves the instrument itself, and it records the call in the journal; do not rebuild "
        "it from the individual tools.\n"
        "Full analysis (buy/sell/hold with reasoning): follow the tradefloor `analyze` skill if "
        "your host has it; its roles call resolve_symbol first, whose `defaults` field holds the "
        "user's settings. Several symbols: scan. Past calls: journal_review. Settings: settings.\n"
        "Numbers come from these tools; never estimate them. Pass as_of (YYYY-MM-DD) for a "
        "historical view, and then ignore output marked point_in_time=false. Low confidence with "
        "no tilt means no edge: say so. End with: Not investment advice. Public data, possibly "
        "delayed; verify before acting."
    ),
)


def _defaults() -> dict:
    """The settings an agent needs to run the desk, whatever host it runs in."""
    return {k: v["value"] for k, v in settings.effective().items()}


def _ctx(symbol: str, as_of: str | None, years: int = 12):
    symbol = validation.symbol(symbol)
    d = data.parse_as_of(as_of)
    code = markets.exchange_for_symbol(symbol)
    ex = markets.EXCHANGES[code]
    df = data.history(symbol, d, years)
    if df.empty:
        raise LookupError(f"No price history for {symbol}. Check the symbol with resolve_symbol.")
    bench = None
    if ex.benchmark and ex.benchmark != symbol.upper():
        b = data.history(ex.benchmark, d, years)
        bench = b if not b.empty else None
    return d, ex, df, bench


def _err(e: Exception) -> dict:
    return {"error": f"{type(e).__name__}: {e}", "category": "invalid_input" if isinstance(e, (ValueError, TypeError, KeyError)) else "unavailable"}


@mcp.tool()
def quick_direction(query: str, horizon: str | None = None, as_of: str | None = None, record: bool = True) -> dict:
    """The standard answer to "which way is X heading?" for any stock, index, ETF, future,
    FX pair or crypto asset, in one call: resolves the instrument, forecasts UP / DOWN /
    SIDEWAYS with probabilities against the base rate, adds key technicals and levels, builds
    a trade plan when the direction is UP or DOWN, and records the call in the journal so it
    can be scored later. Use this first; use the other tools for a deeper analysis.
    horizon defaults to the user's setting; as_of (YYYY-MM-DD) gives a historical view."""
    try:
        res = resolve_symbol(query)
        if "error" in res:
            return res
        note = None
        if "resolved" in res:
            r = res["resolved"]
        else:
            home = res["defaults"]["default_market"]
            c = next((c for c in res["candidates"] if c["exchange_code"] == home), res["candidates"][0])
            r = {"symbol": c["symbol"], "name": c.get("name"), "exchange": c["exchange_code"], "kind": markets.kind_for_symbol(c["symbol"])}
            note = f"Resolved {query!r} by search to {c['symbol']}; other matches: {[x['symbol'] for x in res['candidates'][1:4]]}."
        h = horizon or res["defaults"]["default_horizon"]
        sym = r["symbol"]
        fc = direction_forecast(sym, h, as_of)
        if "error" in fc:
            return fc
        tr = technical_report(sym, as_of)
        p = fc["probabilities"]
        out: dict = {
            "instrument": {k: r.get(k) for k in ("symbol", "name", "exchange", "kind", "currency", "proxies", "price_unit_note") if r.get(k)},
            "as_of": fc["as_of"], "horizon": h, "horizon_trading_days": fc["horizon_trading_days"], "price": fc["price"],
            "direction": fc["direction"], "confidence": fc["confidence"], "probabilities": p,
            "base_rates": fc["base_rates"], "tilt": fc["tilt"], "expected_range_80pct": fc["expected_range_80pct"],
            "similar_setups": fc["similar_setups"], "drivers": fc["drivers"][:3],
            "event_contract": fc["event_contract"], "run": fc["run"],
        }
        if fc.get("setup_vs_outcome"):
            out["setup_vs_outcome"] = fc["setup_vs_outcome"]
        if "error" not in tr:
            out["technicals"] = {k: tr.get(k) for k in ("regime", "trend_strength", "rsi14", "returns_pct", "levels", "range_52w", "relative_strength_vs_benchmark_pct")}
        plan_out = None
        if fc["direction"] in ("UP", "DOWN"):
            plan_out = trade_plan(sym, fc["direction"], h, as_of)
            out["plan"] = plan_out
        if record:
            entry = {"symbol": sym, "as_of": fc["as_of"], "horizon_days": fc["horizon_trading_days"], "price": fc["price"],
                     "direction": fc["direction"], "p_up": p["up"], "p_down": p["down"], "base_p_up": fc["base_rates"]["up"],
                     "p_flat": p["flat"], "event_contract": fc["event_contract"], "base_probabilities": fc["base_rates"],
                     "run_id": fc["run"]["run_id"], "source": "quant"}
            if plan_out and "stop" in plan_out and plan_out.get("side") in ("long", "short"):
                entry.update({"stop": plan_out["stop"], "targets": plan_out.get("targets")})
            out["journal_id"] = journal.record(entry)["id"]
        if note:
            out["note"] = note
        if "no tilt" in fc["tilt"]["label"]:
            out["read"] = "No measurable edge: the probabilities match this instrument's normal behaviour."
        out["disclaimer"] = "Not investment advice. Public data, possibly delayed; verify before acting."
        return out
    except Exception as e:
        return _err(e)


@mcp.tool()
def resolve_symbol(query: str, default_market: str | None = None) -> dict:
    """Turn a ticker, company name or index name into a Yahoo Finance symbol with its
    exchange, currency, timezone, benchmark and (for indices) tradeable proxies.
    Accepts 'RELIANCE', 'NSE:RELIANCE', '7203.T', 'nifty 50', 'S&P 500', 'dax', 'gold', 'bitcoin'.
    default_market is an exchange code (see list_markets) used for bare tickers."""
    try:
        market = (default_market or settings.get("default_market")).upper()
        local = markets.resolve_local(query, market)
        if local:
            df = data.history(local.symbol, None, 1)
            if not df.empty:
                out = local.to_dict()
                i = data.info(local.symbol)
                out["name"] = out.get("name") or i.get("longName") or i.get("shortName")
                out["last_close"] = round(float(df["Close"].iloc[-1]), 4)
                out["last_date"] = str(df.index[-1].date())
                return {"resolved": out, "defaults": _defaults()}
        cands = data.search(query)
        if not cands:
            return {"error": f"Could not resolve {query!r}. Try an explicit Yahoo symbol such as TICKER.NS or TICKER.L."}
        for c in cands:
            c["exchange_code"] = markets.exchange_for_symbol(c["symbol"])
        return {"candidates": cands, "note": "Ambiguous or not a symbol. Pick one and call again with the exact symbol.", "defaults": _defaults()}
    except Exception as e:
        return _err(e)


@mcp.tool()
def list_markets() -> dict:
    """Exchanges tradefloor knows: code, Yahoo suffix, currency and benchmark index."""
    return {"markets": markets.list_markets(), "index_aliases": sorted({a.name for a in markets.INDEX_ALIASES.values()})}


@mcp.tool()
def technical_report(symbol: str, as_of: str | None = None) -> dict:
    """Computed technicals: returns, SMA 20/50/200, regime, ADX, RSI, MACD, Bollinger,
    stochastic, ATR, realized vol and its percentile, 52-week range, drawdown, swing
    support/resistance, relative strength and beta versus the exchange benchmark."""
    try:
        d, ex, df, bench = _ctx(symbol, as_of, years=3)
        out = indicators.technical_summary(df, bench, ex.trading_days)
        out.update({"symbol": symbol, "currency": ex.currency, "benchmark": ex.benchmark})
        return out
    except Exception as e:
        return _err(e)


@mcp.tool()
def direction_forecast(symbol: str, horizon: str = "1m", as_of: str | None = None) -> dict:
    """Probabilities of UP / DOWN / SIDEWAYS over the horizon ('1w', '1m', '3m', '6m' or a
    number of trading days), from how this symbol moved after similar technical setups in
    its own history. Also an 80% expected price range. Deterministic; no LLM involved."""
    try:
        d, ex, df, bench = _ctx(symbol, as_of)
        h = markets.horizon_to_days(horizon, ex.trading_days)
        out = forecast.forecast(df, h, bench)
        out.update({"symbol": symbol, "currency": ex.currency, "horizon": horizon})
        out["data_status"] = {"provider": "Yahoo via yfinance", "capture_time": df.attrs.get("capture_time"),
                              "price_basis": "provider adjusted; only completed daily bars", "benchmark_available": bench is not None,
                              "archival_availability_verified": False}
        out["run"] = runs.create("direction", {"symbol": symbol, "horizon": horizon, "as_of": as_of},
                                 {"prices": snapshots.frame(df), "benchmark": snapshots.frame(bench) if bench is not None else None}, out)
        return out
    except Exception as e:
        return _err(e)


@mcp.tool()
def fundamentals(symbol: str) -> dict:
    """Valuation, profitability, growth, balance sheet, analyst targets, last 5 quarters,
    next earnings date, recent insider transactions. Current snapshot only (point_in_time=false)."""
    try:
        return data.fundamentals(symbol)
    except Exception as e:
        return _err(e)


@mcp.tool()
def news(symbol_or_query: str, as_of: str | None = None, days: int = 14, limit: int = 20) -> dict:
    """Recent headlines from Google News, localized to the instrument's market, filtered to
    items published on or before as_of. Pass a symbol to search by company name, or free text."""
    try:
        d = data.parse_as_of(as_of)
        q, locale = symbol_or_query, "en-US:US"
        looks_symbol = markets.resolve_local(symbol_or_query, settings.get("default_market")) is not None and " " not in symbol_or_query.strip()
        if looks_symbol:
            ex = markets.EXCHANGES[markets.exchange_for_symbol(symbol_or_query)]
            locale = ex.news_locale
            alias = next((a for a in markets.INDEX_ALIASES.values() if a.symbol == symbol_or_query.upper()), None)
            name = alias.name if alias else (data.info(symbol_or_query).get("shortName") or data.info(symbol_or_query).get("longName"))
            if name:
                q = f'"{name}"' if not alias else f"{name} market"
        return data.news(q, locale, d, max(1, min(days, 90)), max(1, min(limit, 50)))
    except Exception as e:
        return _err(e)


@mcp.tool()
def sentiment_signals(symbol: str, include_reddit: bool = False) -> dict:
    """Positioning and crowd signals: analyst recommendation trend, short interest,
    options put/call ratios (where listed options exist). include_reddit adds Reddit
    mentions from the public endpoint, which Reddit often blocks without OAuth; treat an
    error there as "no data". All current-only (point_in_time=false)."""
    try:
        i = data.info(symbol)
        name = i.get("shortName") or i.get("longName") or symbol
        out = {
            "symbol": symbol,
            "point_in_time": False,
            "analyst_recommendations_by_month": data.analyst_trend(symbol),
            "recommendation_key": i.get("recommendationKey"),
            "short_percent_of_float": i.get("shortPercentOfFloat"),
            "short_ratio_days": i.get("shortRatio"),
            "options": data.options_positioning(symbol),
        }
        if include_reddit:
            out["reddit"] = data.reddit_mentions(f'"{name}" OR {symbol.split(".")[0]}')
        return out
    except Exception as e:
        return _err(e)


@mcp.tool()
def macro_context(symbol: str, as_of: str | None = None) -> dict:
    """The market backdrop for an instrument: its exchange benchmark and volatility index,
    US 10Y yield, dollar index, local currency vs USD, crude and gold. Each with last value
    and 1-month / 3-month change, all truncated at as_of."""
    try:
        d = data.parse_as_of(as_of)
        ex = markets.EXCHANGES[markets.exchange_for_symbol(symbol)]
        series = {"benchmark": ex.benchmark, "volatility_index": ex.vol_index, "us_10y_yield_x10": "^TNX",
                  "dollar_index": "DX-Y.NYB", "local_ccy_per_usd": ex.fx_vs_usd, "wti_crude": "CL=F", "gold": "GC=F", "sp500": "^GSPC"}
        out: dict = {"exchange": ex.code, "as_of": str(d or date.today())}
        for label, sym in series.items():
            if not sym:
                continue
            h = data.history(sym, d, 2)
            if h.empty:
                out[label] = {"symbol": sym, "error": "no data"}
                continue
            c = h["Close"]
            row = {"symbol": sym, "last": round(float(c.iloc[-1]), 4), "date": str(h.index[-1].date())}
            if len(c) > 22:
                row["chg_1m_pct"] = round((float(c.iloc[-1]) / float(c.iloc[-22]) - 1) * 100, 2)
            if len(c) > 64:
                row["chg_3m_pct"] = round((float(c.iloc[-1]) / float(c.iloc[-64]) - 1) * 100, 2)
            if label in ("benchmark", "sp500") and len(c) > 200:
                row["above_200d"] = bool(c.iloc[-1] > c.tail(200).mean())
            if label == "volatility_index" and len(c) > 250:
                row["percentile_1y"] = round(float((c.tail(252) <= c.iloc[-1]).mean()), 2)
            out[label] = row
        return out
    except Exception as e:
        return _err(e)


@mcp.tool()
def trade_plan(symbol: str, direction: str, horizon: str = "1m", as_of: str | None = None,
               capital: float | None = None, risk_pct: float | None = None, lot_size: int = 1,
               allow_short: bool = False, quote_currency: str | None = None, quote_unit_scale: float | None = None,
               contract_multiplier: float | None = None, fx_to_account: float | None = None,
               quantity_step: float | None = None, cost_bps: float = 0.0, fx_as_of: str | None = None) -> dict:
    """Entry zone, ATR-based stop, targets with reward:risk, time stop and position size for
    a directional view (UP / DOWN / SIDEWAYS). Capital and risk default to the user's plugin
    config. Sizing risks risk_pct of capital to the stop, capped at the max position size."""
    try:
        validation.direction(direction)
        if capital is not None:
            validation.number(capital, "capital", 0)
        d, ex, df, bench = _ctx(symbol, as_of, years=12)
        h = markets.horizon_to_days(horizon, ex.trading_days)
        fc = forecast.forecast(df, h, bench)
        a = float(indicators.atr(df).iloc[-1])
        cap = settings.get("capital") if capital is None else capital
        account = settings.get("account_currency") or markets.EXCHANGES[settings.get("default_market")].currency
        kind = markets.kind_for_symbol(symbol)
        quote = (quote_currency or ex.currency or "").upper()
        if quote and (len(quote) != 3 or not quote.isalpha()):
            raise ValueError("quote_currency must be a three-letter currency code")
        scale, mult, fx = quote_unit_scale, contract_multiplier, fx_to_account
        reason = None
        if ex.price_unit_note and scale is None:
            reason = "Explicit verified quote_unit_scale required for pence/cents/agorot venues"
        if kind == "future" and mult is None:
            reason = "Explicit contract_multiplier required; a continuous futures series is not an executable contract"
        if quote != account:
            if fx is None or fx_as_of is None:
                reason = "Explicit fx_to_account and fx_as_of required for cross-currency capital"
            else:
                fx_day = date.fromisoformat(validation.iso_date(fx_as_of, "fx_as_of"))
                if not 0 <= (date.today()-fx_day).days <= 7:
                    reason = "FX receipt must be dated within seven days; sizing disabled"
        if kind == "future":
            reason = "Continuous futures are analytical only; use a contract-specific adapter before sizing"
        if not quote:
            reason = "Explicit quote_currency required for this instrument"
        if d and cap:
            reason = "Historical adjusted prices are analytical references, not executable quotes; sizing disabled"
        out = plan.build_plan(
            price=float(df["Close"].iloc[-1]), atr=a, direction=direction, horizon_days=h,
            capital=0 if reason else cap,
            risk_pct=settings.get("risk_per_trade_pct") if risk_pct is None else risk_pct,
            max_position_pct=settings.get("max_position_pct"), lot_size=lot_size,
            range_high=fc["expected_range_80pct"]["high"], range_low=fc["expected_range_80pct"]["low"],
            allow_short=allow_short,
            quote_unit_scale=1 if scale is None else scale, contract_multiplier=1 if mult is None else mult,
            fx_to_account=1 if fx is None else fx, quantity_step=quantity_step, cost_bps=cost_bps,
        )
        out["account_currency"] = account
        out["quote_currency"] = quote
        out["sizing_status"] = "blocked: " + reason if reason else out.get("sizing_status", "unit-normalized arithmetic; verify instrument metadata and executable quote")
        out["fx_receipt"] = {"rate": fx, "as_of": fx_as_of, "source": "caller supplied; not independently verified"} if fx is not None else None
        out["price_basis"] = "provider-adjusted analytical close; plan levels are conditional reference levels"
        out.update({"symbol": symbol, "currency": ex.currency, "price": round(float(df["Close"].iloc[-1]), 4), "atr14": round(a, 4), "horizon_trading_days": h})
        if markets.kind_for_symbol(symbol) == "index":
            alias = next((x for x in markets.INDEX_ALIASES.values() if x.symbol == symbol.upper()), None)
            proxies = list(alias.proxies) if alias else []
            out["index_note"] = (
                "An index level is not tradeable. Use these levels for timing, and call trade_plan on a proxy "
                f"to size a position{': ' + ', '.join(proxies) if proxies else ''}. Index futures need lot_size set."
            )
            out.pop("sizing", None)
        return out
    except Exception as e:
        return _err(e)


@mcp.tool()
def scan(symbols: list[str], horizon: str = "1m", as_of: str | None = None) -> dict:
    """Rank up to 40 symbols by tilt: how much more bullish (or bearish) today's setup is than
    each symbol's own base rate, from the quant direction forecast. Cheap first pass before a
    full analysis. Returns direction, probabilities, edge and confidence per symbol."""
    if not isinstance(symbols, list) or not 1 <= len(symbols) <= 40:
        return _err(ValueError("scan requires 1..40 ticker symbols"))
    rows, errors = [], []
    for s in symbols[:40]:
        r = direction_forecast(s, horizon, as_of)
        if "error" in r:
            errors.append({"symbol": s, "error": r["error"]})
            continue
        p = r["probabilities"]
        rows.append({"symbol": s, "direction": r["direction"], "confidence": r["confidence"], "p_up": p["up"], "p_down": p["down"],
                     "net": round(p["up"] - p["down"], 3), "tilt": r["tilt"]["value"], "edge": r["edge_vs_base_rate"], "price": r["price"],
                     "range_80pct": [r["expected_range_80pct"]["low"], r["expected_range_80pct"]["high"]]})
    rows.sort(key=lambda x: -x["tilt"])
    return {"horizon": horizon, "as_of": as_of or str(date.today()), "ranked": rows, "errors": errors}


@mcp.tool()
def intraday_scan(market: str, top: int = 8, at: str | None = None, size: int | None = None, side: str = "both",
                  min_rvol: float = 0.8, mode: str = "auto") -> dict:
    """Intraday stock scouting for a market: 'nifty 50', 'bank nifty', 's&p 500', 'nasdaq 100',
    'dax', 'ftse 100', 'japan', 'hong kong', 'china', other country or index names, or two
    or more symbols separated by commas.
    Before the open (or when closed): a pre-market watchlist of stocks likely to make a BIG
    move in the coming session (in play yesterday: traded value and range above normal),
    with the calibrated chance of a big move against the universe, a direction lean only
    when the data shows one, and a two-sided opening-range plan.
    During the session (15+ minutes in): a live scan ranking stocks by directional momentum
    (relative volume, move efficiency, VWAP side, opening-range break, strength against the
    index) with calibrated follow-through probabilities and trigger-based plans.
    mode: auto, premarket or live. at='YYYY-MM-DD HH:MM' (exchange time, within ~55 days)
    replays a past moment point-in-time. side: both, long or short."""
    try:
        return scout.run(market, top=validation.integer(top, "top", 1, 20), at=at, size=size, side=side, min_rvol=min_rvol, mode=mode)
    except Exception as e:
        return _err(e)


@mcp.tool()
def swarm_roster(symbol: str) -> dict:
    """The participant groups of the market swarm for this instrument's market (for example
    foreign institutions, domestic funds, retail, prop desks, market makers, event funds),
    with each group's behaviour and a description to brief a persona agent. Weights are
    illustrative defaults, not measured shares."""
    try:
        code = markets.exchange_for_symbol(symbol)
        return {"symbol": symbol, "exchange": code,
                "groups": [{"id": g.id, "name": g.name, "weight": round(g.weight, 3), "description": g.description,
                            "behaviour": {"fundamental": g.k_fundamental, "trend": g.k_trend, "news": g.k_news, "participation": g.participation}}
                           for g in swarm.roster(code)],
                "reaction_fields": {"group": "group id", "sentiment": "-1 very bearish .. +1 very bullish",
                                    "conviction": "0 split crowd .. 1 unanimous", "persistence_days": "half-life of the reaction, 0.5 to 60",
                                    "fair_value_shift_pct": "how far the group now thinks fair value is from today's price, -50 to 50"}}
    except Exception as e:
        return _err(e)


@mcp.tool()
def swarm_simulate(symbol: str, horizon: str = "1m", reactions: list[dict] | None = None, as_of: str | None = None,
                   worlds: int = 1000, agents: int = 2000, seed: int = 7, weights: dict | None = None) -> dict:
    """Agent-based market simulation for one instrument: `agents` simulated traders across
    the market's participant groups trade every day of the horizon in `worlds` Monte Carlo
    runs, calibrated to the stock's own volatility, tails and normal drift. Without
    reactions it returns the baseline (normal behaviour). With reactions (one per group:
    sentiment, conviction, persistence_days, fair_value_shift_pct; see swarm_roster) it
    returns the scenario, the shift against the baseline, a fan of paths, and which group
    moved the price. Same seed, same answer. For a what-if, call it again with the
    reactions to the injected event and compare."""
    try:
        d, ex, df, bench = _ctx(symbol, as_of, years=12)
        h = markets.horizon_to_days(horizon, ex.trading_days)
        out = swarm.run(df, ex.code, h, reactions, runs=worlds, agents=agents,
                        seed=seed, weights=weights)
        out.update({"symbol": symbol, "currency": ex.currency, "as_of": str(df.index[-1].date()), "horizon": horizon,
                    "caveats": ["The simulation spreads outcomes around the stock's normal behaviour; it does not know the future.",
                                "Reactions come from persona agents or a what-if; their skill is measured by the journal (source 'swarm').",
                                "Group weights and the news-impact scale are assumptions, listed under 'assumptions'."]})
        out["run"] = runs.create("swarm", {"symbol": symbol, "horizon": horizon, "reactions": reactions,
                                            "worlds": worlds, "agents": agents, "seed": seed, "weights": weights},
                                 {"prices": snapshots.frame(df), "exchange": ex.code}, out)
        return out
    except Exception as e:
        return _err(e)


@mcp.tool()
def journal_record(entry: dict) -> dict:
    """Log a final call so it can be scored later. Required keys: symbol, as_of,
    horizon_days, price, direction, p_up, p_down. Recommended: base_p_up, flat_band_pct,
    rating, stop, targets, run_dir, source ('quant', 'full' or 'swarm').
    Intraday live calls: kind='intraday', symbol, exchange, mode='live', direction ('LONG'
    or 'SHORT'), trigger, stop, targets, p_follow, signal_time ('YYYY-MM-DD HH:MM').
    Pre-market picks: kind='intraday', symbol, exchange, mode='premarket', direction
    ('EITHER', 'LONG' or 'SHORT'), target_session (YYYY-MM-DD), p_big_move, adr_pct (as a
    fraction, e.g. 0.021), prev_close. They are graded on the target session: big move or
    not, and a two-sided 15-minute opening-range trade."""
    try:
        e = journal.record(entry)
        return {"recorded": e, "path": str(journal.journal_path())}
    except Exception as e:
        return _err(e)


@mcp.tool()
def journal_review(symbol: str | None = None) -> dict:
    """Score every logged call whose horizon has elapsed: realized return, hit or miss,
    Brier score for p_up, stop hit, and aggregate hit rate against the base-rate reference."""
    try:
        entries = [e for e in journal.load() if not symbol or e["symbol"].upper() == symbol.upper()]
        scored = []
        for e in entries:
            try:
                if e.get("kind") == "intraday":
                    scored.append(_score_intraday(e))
                else:
                    scored.append(journal.score_entry(e, data.bars_after(e["symbol"], e["as_of"], int(e["horizon_days"]), float(e["price"]))))
            except Exception as ex:
                scored.append({"id": e.get("id"), "symbol": e.get("symbol"), "status": "error", "error": str(ex)})
        daily = [s for s, e in zip(scored, entries) if e.get("kind") != "intraday"]
        out = {"path": str(settings.home() / "journal.sqlite3"), "legacy_export_path": str(journal.journal_path()),
               "summary": journal.summarize(daily, [e for e in entries if e.get("kind") != "intraday"]), "calls": scored}
        intra = journal.summarize_intraday(scored)
        if intra:
            out["intraday_summary"] = intra
        return out
    except Exception as e:
        return _err(e)


@mcp.tool(name="settings")
def settings_tool(key: str | None = None, value: str | None = None) -> dict:
    """Show or change the user's tradefloor settings: default_market, default_horizon,
    capital, risk_per_trade_pct, max_position_pct, debate_rounds. With no arguments,
    returns every setting, its value and where it came from. With key and value, saves it
    to ~/.tradefloor/config.json, which every agent host shares. Only change a setting
    when the user asks to."""
    try:
        if key is None:
            return {"settings": settings.effective(), "path": str(settings.config_path())}
        if value is None:
            return {key: settings.effective()[key]}
        return settings.set_value(key, value)
    except Exception as e:
        return _err(e)


def _score_intraday(e: dict) -> dict:
    """Pick the session an intraday call was meant for, from the bars after it became valid."""
    import pandas as pd
    from zoneinfo import ZoneInfo

    ex = markets.EXCHANGES[e["exchange"]]
    tz = ZoneInfo(ex.tz)
    bars = data.intraday_bars([e["symbol"]], tz=ex.tz).get(e["symbol"])
    if bars is None or bars.empty:
        return {"id": e.get("id"), "symbol": e["symbol"], "kind": "intraday", "status": "no data"}
    bars = calendars.filter_bars(intraday.truncate_at(bars, datetime_now(tz)), ex.code, ex.tz)
    sess = intraday.sessions(bars)
    close_hhmm = intraday.typical_close_time(sess)
    now = datetime_now(tz)
    if e["mode"] == "premarket":
        target = pd.Timestamp(str(e["target_session"])[:10]).date()
        sch = calendars.session(ex.code, target, ex.tz)
        if sch["date"] != str(target):
            return {"id": e.get("id"), "symbol": e["symbol"], "kind": "intraday", "status": "no data", "error": "target is not a scheduled session"}
        close_hhmm = datetime.fromisoformat(sch["close"]).strftime("%H:%M")
        day = [s for s in sess if s.index[0].date() == target]
        base = {"id": e.get("id"), "symbol": e["symbol"], "kind": "intraday", "mode": "premarket", "session": str(target)}
        done = target < now.date() or (close_hhmm is not None and now.strftime("%H:%M") >= close_hhmm)
        if not done:
            return {**base, "status": "open"}
        if not day:
            return {**base, "status": "no data", "error": "missing target session; Yahoo intraday retention is limited"}
        coverage = calendars.session_coverage(day[0], ex.code, str(target), ex.tz)
        if not coverage["complete"]:
            return {**base, "status": "no data", "coverage": coverage}
        side = e["direction"] if e["direction"] in ("LONG", "SHORT") else None
        orb = premarket.simulate_orb(day[0], float(e["adr_pct"]) * float(e["prev_close"]), side,
                                    cost_bps=float(e.get("cost_bps", 0)), slippage_bps=float(e.get("slippage_bps", 0)),
                                    square_off=e.get("square_off"))
        big = premarket.outcome(day[0], float(e["adr_pct"]))["big_move"]
        res = {**base, **orb, "orb": orb.get("status"), "status": "scored", "big_move": bool(big)}
        if orb.get("triggered"):
            res["hit"] = orb["r_multiple"] > 0
        if e.get("p_big_move") is not None:
            res["brier_big_move"] = round((float(e["p_big_move"]) - (1.0 if big else 0.0)) ** 2, 4)
        return res
    if e["mode"] == "live":
        t = pd.Timestamp(e["signal_time"]).tz_localize(tz)
        day = [s for s in sess if s.index[0].date() == t.date()]
        seg = day[0][day[0].index >= t] if day else pd.DataFrame()
        target_date = t.date()
        sch = calendars.session(ex.code, target_date, ex.tz)
        close_hhmm = datetime.fromisoformat(sch["close"]).strftime("%H:%M")
    complete = target_date is not None and (target_date < now.date() or (close_hhmm is not None and now.strftime("%H:%M") >= close_hhmm))
    if complete:
        coverage = calendars.session_coverage(day[0] if day else pd.DataFrame(), ex.code, str(target_date), ex.tz)
        if not coverage["complete"]:
            return {"id":e.get("id"),"symbol":e["symbol"],"kind":"intraday","status":"no data","coverage":coverage}
    return journal.score_intraday({**e, "session_date": str(target_date) if target_date else None}, seg, complete)


def datetime_now(tz):
    from datetime import datetime

    return datetime.now(tz)


@mcp.tool()
def scenario_lab(case: str = "earnings", sentiment: float | None = None, persistence: float | None = None,
                 retail_weight: float = .2, seed: int = 7, worlds: int = 300, sensitivity: bool = True,
                 price_snapshot: dict | None = None, evidence: list[dict] | None = None) -> dict:
    """Offline scenario lab: three fictional cases, frozen inputs, competing baselines,
    evidence graph, assumption fragility and falsification. No API key or LLM required.
    Optional OHLCV snapshot replaces fictional history; its availability is unverified."""
    try:
        return lab.simulate(case, sentiment, persistence, retail_weight, seed, worlds, sensitivity,
                            price_snapshot=price_snapshot, evidence=evidence)
    except Exception as e:
        return _err(e)


@mcp.tool()
def scenario_fork(run_id: str, overrides: dict) -> dict:
    """Fork a frozen scenario; change sentiment, persistence, retail_weight, seed, worlds
    or sensitivity. Saves a new immutable bundle referencing its parent."""
    try:
        return lab.fork(run_id, overrides)
    except Exception as e:
        return _err(e)


@mcp.tool()
def run_bundle(run_id: str | None = None, bundle: dict | None = None, bundle_json: str | None = None) -> dict:
    """Read/export a hashed immutable run, or import a bundle after verifying its hash.
    Bundles are data only. Market snapshots may require permission before redistribution."""
    try:
        if sum(v is not None for v in (run_id, bundle, bundle_json)) != 1:
            raise ValueError("supply exactly one of run_id, bundle or bundle_json")
        if bundle_json is not None:
            import json
            if len(bundle_json.encode("utf-8")) > 20_000_000:
                raise ValueError("bundle exceeds 20 MB")
            bundle = json.loads(bundle_json)
        return runs.read(run_id) if run_id else runs.import_bundle(bundle)
    except Exception as e:
        return _err(e)


@mcp.tool()
def run_replay(run_id: str) -> dict:
    """Recompute quant, swarm or scenario results from stored prices, without network data.
    Records a child run. Reproducibility depends on the recorded runtime/model version."""
    try:
        b = runs.read(run_id)
        if b["kind"] == "scenario":
            return lab.fork(run_id, {})
        if b["kind"] == "market-sandbox":
            out = microstructure.simulate(**b["request"])
            out["run"] = runs.create(b["kind"], b["request"], b["inputs"], out, run_id)
            return out
        df = snapshots.restore(b["inputs"]["prices"])
        r = b["request"]
        if b["kind"] == "direction":
            bench = snapshots.restore(b["inputs"]["benchmark"]) if b["inputs"].get("benchmark") else None
            out = forecast.forecast(df, b["result"]["horizon_trading_days"], bench)
        elif b["kind"] == "swarm":
            out = swarm.run(df, b["inputs"]["exchange"], b["result"]["event_contract"]["horizon_days"],
                            r.get("reactions"), runs=r["worlds"], agents=r["agents"], seed=r["seed"], weights=r.get("weights"))
        else:
            raise ValueError("this run kind does not support numerical replay")
        out["run"] = runs.create(b["kind"], r, b["inputs"], out, run_id)
        return out
    except Exception as e:
        return _err(e)


@mcp.tool()
def run_begin(kind: str, request: dict) -> dict:
    """Allocate a unique desk workspace and immutable request receipt. Roles write their
    reports in workspace; repeated symbol/date runs never overwrite earlier reports."""
    try:
        if kind not in ("analyze", "scout", "swarm-desk"):
            raise ValueError("kind must be analyze, scout or swarm-desk")
        receipt = runs.create(kind, request, runs.desk_inputs(), {})
        workspace = runs.root() / receipt["run_id"] / "reports"
        workspace.mkdir()
        return {**receipt, "workspace": str(workspace)}
    except Exception as e:
        return _err(e)


@mcp.tool()
def run_finalize(run_id: str, decision: dict) -> dict:
    """Freeze a desk's report files and decision into a hashed child bundle. Reads only
    bounded text files inside the allocated workspace; later edits do not alter the receipt."""
    try:
        return runs.finalize(run_id, decision)
    except Exception as e:
        return _err(e)


@mcp.tool()
def evidence_audit(evidence: list[dict], claims: list[dict], cutoff: str) -> dict:
    """Validate evidence availability timestamps, duplicate content and claim citations.
    Measurement/source nodes need published_at AND available_at. Does not verify truth."""
    try:
        return lab.evidence_graph(evidence, claims, cutoff)
    except Exception as e:
        return _err(e)


@mcp.tool()
def decision_validate(prior: dict, adjusted: dict, evidence: list[dict], adjustments: list[dict]) -> dict:
    """Enforce normalized probabilities, total per-class adjustment <=0.10, evidence IDs,
    aggregate deltas and deterministic direction. No model-generated arithmetic trusted."""
    try:
        return validation.decision(prior, adjusted, evidence, adjustments)
    except Exception as e:
        return _err(e)


@mcp.tool()
def falsification_check(conditions: list[dict], observations: dict | None = None) -> dict:
    """Evaluate explicit above/below thesis failure conditions; report missing observations."""
    try:
        return lab.falsification(conditions, observations)
    except Exception as e:
        return _err(e)


@mcp.tool()
def forecast_evaluation(cases: list[dict]) -> dict:
    """Paired 3-class Brier/log loss, reliability and date-clustered uncertainty. Each case
    requires as_of, probabilities, reference and outcome. Never proves a trading edge."""
    try:
        return evaluation.compare(cases)
    except Exception as e:
        return _err(e)


@mcp.tool()
def learning_review(training: list[dict], validation_cases: list[dict]) -> dict:
    """Review training versus later untouched cases with explicit horizon embargo;
    insufficient evidence retains the baseline. Never automatically changes a model."""
    try:
        return evaluation.learning_gate(training, validation_cases)
    except Exception as e:
        return _err(e)


@mcp.tool()
def portfolio_stress(holdings: list[dict], shocks: dict, account_currency: str,
                     correlation: list[list[float]] | None = None) -> dict:
    """Stress account-currency holdings under supplied shocks, concentration and optional
    positive-semidefinite correlations. Values/volatility are caller assumptions."""
    try:
        return portfolio.stress(holdings, shocks, account_currency, correlation)
    except Exception as e:
        return _err(e)


@mcp.tool()
def experiment_record(experiment: dict) -> dict:
    """Register forecast, abstained or failed status with actual registration timestamp.
    Prospective status is derived from date, not asserted by a caller. Local only."""
    try:
        return registry.record(experiment)
    except Exception as e:
        return _err(e)


@mcp.tool()
def experiment_settle(identifier: str, outcome: str) -> dict:
    """Append an immutable caller-supplied settlement. Use the frozen event definition;
    this manual outcome is not independently verified or a public proof of performance."""
    try:
        return registry.settle(identifier, outcome)
    except Exception as e:
        return _err(e)


@mcp.tool()
def experiment_scoreboard() -> dict:
    """Export all registered statuses and paired evaluations; never omit failures/abstentions."""
    try:
        return registry.scoreboard()
    except Exception as e:
        return _err(e)


@mcp.tool()
def experiment_capture(symbol: str, horizon: str = "1w", include_swarm: bool = True) -> dict:
    """Collect quant and no-reaction swarm on identical frozen data, register failures too.
    Explicit local collection; no scheduler, orders or automatic public upload."""
    import uuid
    try:
        symbol = validation.symbol(symbol)
        key = uuid.uuid4().hex
        base = {"symbol": symbol, "as_of": str(date.today()), "experiment_key": key}
        rows = []
        fc = direction_forecast(symbol, horizon)
        if "error" in fc:
            for source in (["quant", "swarm-baseline"] if include_swarm else ["quant"]):
                rows.append(registry.record({**base, "source": source, "status": "failed", "reason": fc["error"]}))
            return {"experiments": rows, "collection_status": "failed; retained in registry"}
        base["as_of"] = fc["as_of"]
        common = {**base, "reference": fc["base_rates"], "event_contract": fc["event_contract"], "status": "forecast"}
        rows.append(registry.record({**common, "source": "quant", "probabilities": fc["probabilities"], "run_id": fc["run"]["run_id"]}))
        if include_swarm:
            try:
                frozen = runs.read(fc["run"]["run_id"])
                out = swarm.run(snapshots.restore(frozen["inputs"]["prices"]), markets.exchange_for_symbol(symbol),
                                fc["horizon_trading_days"], runs=300, agents=200, seed=7)
                if runs.digest(out["event_contract"]) != runs.digest(fc["event_contract"]):
                    raise ValueError("swarm/quant event definitions differ; comparison refused")
                p = out["baseline"]
                rows.append(registry.record({**common, "source": "swarm-baseline", "probabilities": {"up":p["p_up"],"down":p["p_down"],"flat":p["p_flat"]},
                                             "run_id": fc["run"]["run_id"], "swarm_model": out["model"]}))
            except Exception as e:
                rows.append(registry.record({**base, "source": "swarm-baseline", "status":"failed","reason":str(e)}))
        return {"experiments": rows, "note": "Externally timestamp commitments before outcomes for a public prospective record; a local hash chain is insufficient."}
    except Exception as e:
        return _err(e)


@mcp.tool()
def experiment_mature() -> dict:
    """Settle registered daily forecasts whose horizons elapsed using rebased Yahoo adjusted
    prices. Append-only; errors remain visible. Does not correct earlier settlements."""
    try:
        report = registry.scoreboard()
        results = []
        for e in report["experiments"]:
            if e["status"] != "forecast" or e["settlement"]:
                continue
            try:
                event = events.validate(e["event_contract"])
                after = data.bars_after(e["symbol"], e["as_of"], event["horizon_days"], event["reference_price"])
                if len(after) < event["horizon_days"]:
                    results.append({"id":e["id"],"status":"open"})
                    continue
                price = float(after["Close"].iloc[-1])
                import math
                value = math.log(price/event["reference_price"]) if event["return_convention"] == "log" else price/event["reference_price"]-1
                outcome = events.label(value,event["flat_band"])
                results.append(registry.settle(e["id"], outcome, "Yahoo adjusted history rebased to saved anchor; unofficial provider", str(after.index[-1].date())))
            except Exception as ex:
                results.append({"id":e["id"],"status":"error","error":str(ex)})
        return {"results":results,"scoreboard":registry.scoreboard()}
    except Exception as e:
        return _err(e)


@mcp.tool()
def market_sandbox(steps: int = 120, seed: int = 7, reactions: list[dict] | None = None,
                   liquidity: float = 1, persistence: float = 20) -> dict:
    """Experimental synthetic limit order book with cash/inventory constraints, cancellation,
    price-time priority and conserved ledgers. Separate from the calibrated-return swarm;
    not an exchange replica or a forecast. Inspect tape, executions and participant budgets."""
    try:
        request = {"steps": steps, "seed": seed, "reactions": reactions, "liquidity": liquidity, "persistence": persistence}
        out = microstructure.simulate(**request)
        out["run"] = runs.create("market-sandbox", request, {"data_kind": "synthetic"}, out)
        return out
    except Exception as e:
        return _err(e)


@mcp.tool()
def journal_export() -> dict:
    """Export the transactional journal to interoperable JSONL, atomically."""
    try:
        return journal.export()
    except Exception as e:
        return _err(e)


from . import research_tools
research_tools.register(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
