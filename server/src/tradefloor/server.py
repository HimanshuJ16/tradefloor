"""tradefloor MCP server. stdio transport; works with any MCP host.

Every tool returns a JSON object. Failures come back as {"error": ...} so an agent can
report the gap instead of filling it in.
"""

from __future__ import annotations

from datetime import date

from mcp.server.mcpserver import MCPServer

from . import data, forecast, indicators, intraday, journal, markets, plan, premarket, scout, settings

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
    return {"error": f"{type(e).__name__}: {e}"}


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
                     "flat_band_pct": round(0.25 * fc["volatility"]["horizon_1sigma_pct"], 3), "source": "quant"}
            if plan_out and "stop" in plan_out:
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
               allow_short: bool = False) -> dict:
    """Entry zone, ATR-based stop, targets with reward:risk, time stop and position size for
    a directional view (UP / DOWN / SIDEWAYS). Capital and risk default to the user's plugin
    config. Sizing risks risk_pct of capital to the stop, capped at the max position size."""
    try:
        d, ex, df, bench = _ctx(symbol, as_of, years=12)
        h = markets.horizon_to_days(horizon, ex.trading_days)
        fc = forecast.forecast(df, h, bench)
        a = float(indicators.atr(df).iloc[-1])
        out = plan.build_plan(
            price=float(df["Close"].iloc[-1]), atr=a, direction=direction, horizon_days=h,
            capital=settings.get("capital") if capital is None else capital,
            risk_pct=settings.get("risk_per_trade_pct") if risk_pct is None else risk_pct,
            max_position_pct=settings.get("max_position_pct"), lot_size=lot_size,
            range_high=fc["expected_range_80pct"]["high"], range_low=fc["expected_range_80pct"]["low"],
            allow_short=allow_short,
        )
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
        return scout.run(market, top=max(1, min(top, 20)), at=at, size=size, side=side, min_rvol=min_rvol, mode=mode)
    except Exception as e:
        return _err(e)


@mcp.tool()
def journal_record(entry: dict) -> dict:
    """Log a final call so it can be scored later. Required keys: symbol, as_of,
    horizon_days, price, direction, p_up, p_down. Recommended: base_p_up, flat_band_pct,
    rating, stop, targets, run_dir, source ('quant' or 'full').
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
                    scored.append(journal.score_entry(e, data.bars_after(e["symbol"], e["as_of"], int(e["horizon_days"]))))
            except Exception as ex:
                scored.append({"id": e.get("id"), "symbol": e.get("symbol"), "status": "error", "error": str(ex)})
        daily = [s for s, e in zip(scored, entries) if e.get("kind") != "intraday"]
        out = {"path": str(journal.journal_path()),
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
    sess = intraday.sessions(bars)
    close_hhmm = intraday.typical_close_time(sess)
    now = datetime_now(tz)
    if e["mode"] == "premarket":
        target = pd.Timestamp(str(e["target_session"])[:10]).date()
        day = [s for s in sess if s.index[0].date() == target]
        base = {"id": e.get("id"), "symbol": e["symbol"], "kind": "intraday", "mode": "premarket", "session": str(target)}
        done = bool(day) and (target < now.date() or (close_hhmm is not None and now.strftime("%H:%M") >= close_hhmm))
        if not done:
            return {**base, "status": "open"}
        side = e["direction"] if e["direction"] in ("LONG", "SHORT") else None
        orb = premarket.simulate_orb(day[0], float(e["adr_pct"]) * float(e["prev_close"]), side)
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
    complete = target_date is not None and (target_date < now.date() or (close_hhmm is not None and now.strftime("%H:%M") >= close_hhmm))
    return journal.score_intraday({**e, "session_date": str(target_date) if target_date else None}, seg, complete)


def datetime_now(tz):
    from datetime import datetime

    return datetime.now(tz)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
