"""Data access. Yahoo Finance via yfinance for prices and fundamentals; Google News RSS
and Reddit's public JSON for headlines. No API keys.

Point-in-time rule: every dated call takes `as_of` and returns nothing after it. Sources
that cannot honour that (yfinance fundamentals, analyst targets, short interest, option
chains) are marked `point_in_time: false`, and the agents are told to ignore them when
`as_of` is in the past.
"""

from __future__ import annotations

import contextlib
import json
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import numpy as np
import pandas as pd

_CACHE: dict[tuple, tuple[float, object]] = {}
_TTL = 15 * 60
_UA = "Mozilla/5.0 (tradefloor; +https://github.com/HimanshuJ16/tradefloor)"


def _cached(key: tuple, fn):
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    val = fn()
    _CACHE[key] = (time.time(), val)
    return val


@contextlib.contextmanager
def _quiet():
    """yfinance and friends sometimes print. stdout is the MCP channel, so route it away."""
    with contextlib.redirect_stdout(sys.stderr):
        yield


def _yf():
    import yfinance as yf  # imported lazily so offline tests never need the network stack

    return yf


def parse_as_of(as_of: str | None) -> date | None:
    if as_of in (None, "", "today", "now"):
        return None
    d = datetime.strptime(str(as_of)[:10], "%Y-%m-%d").date()
    if d > date.today():
        raise ValueError(f"as_of {d} is in the future")
    return d


def history(symbol: str, as_of: date | None = None, years: int = 12) -> pd.DataFrame:
    """Daily OHLCV, split and dividend adjusted, truncated at as_of (inclusive)."""

    def fetch():
        end = (as_of or date.today()) + timedelta(days=1)
        start = end - timedelta(days=int(365.25 * years))
        with _quiet():
            df = _yf().Ticker(symbol).history(start=start.isoformat(), end=end.isoformat(), interval="1d", auto_adjust=True)
        if df is None or df.empty:
            return pd.DataFrame()
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df.index = pd.to_datetime(df.index).normalize()
        df = df[~df.index.duplicated(keep="last")].dropna(subset=["Close"])
        if as_of:
            df = df[df.index <= pd.Timestamp(as_of)]
        return df

    return _cached(("hist", symbol, as_of, years), fetch)


def bars_after(symbol: str, after: str, n: int) -> pd.DataFrame:
    start = datetime.strptime(after[:10], "%Y-%m-%d").date()
    df = history(symbol, None, years=max(1, (date.today() - start).days // 365 + 1))
    return df[df.index > pd.Timestamp(start)].head(n)


def info(symbol: str) -> dict:
    def fetch():
        with _quiet():
            try:
                return _yf().Ticker(symbol).info or {}
            except Exception:
                return {}

    return _cached(("info", symbol), fetch)


def search(query: str, limit: int = 8) -> list[dict]:
    with _quiet():
        try:
            res = _yf().Search(query, max_results=limit, news_count=0)
            quotes = res.quotes or []
        except Exception:
            return []
    return [
        {"symbol": q.get("symbol"), "name": q.get("longname") or q.get("shortname"), "exchange": q.get("exchDisp") or q.get("exchange"), "type": q.get("quoteType")}
        for q in quotes
        if q.get("symbol")
    ]


def _num(x, nd: int = 4):
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(f) or np.isinf(f) else round(f, nd)


_FUND_KEYS = [
    "longName", "sector", "industry", "country", "currency", "financialCurrency", "marketCap", "enterpriseValue",
    "trailingPE", "forwardPE", "priceToBook", "priceToSalesTrailing12Months", "enterpriseToEbitda", "pegRatio",
    "trailingEps", "forwardEps", "profitMargins", "operatingMargins", "grossMargins", "returnOnEquity", "returnOnAssets",
    "revenueGrowth", "earningsGrowth", "earningsQuarterlyGrowth", "debtToEquity", "currentRatio", "quickRatio",
    "totalCash", "totalDebt", "freeCashflow", "operatingCashflow", "dividendYield", "payoutRatio", "beta",
    "heldPercentInsiders", "heldPercentInstitutions", "shortPercentOfFloat", "shortRatio",
    "targetMeanPrice", "targetLowPrice", "targetHighPrice", "recommendationKey", "numberOfAnalystOpinions",
]


def fundamentals(symbol: str) -> dict:
    i = info(symbol)
    out: dict = {"symbol": symbol, "point_in_time": False, "note": "Current snapshot from Yahoo Finance. Not valid for past as_of dates."}
    for k in _FUND_KEYS:
        v = i.get(k)
        if v is not None:
            out[k] = v if isinstance(v, str) else _num(v)
    if i.get("quoteType") in ("INDEX", "CURRENCY", "FUTURE", "CRYPTOCURRENCY"):
        out["note"] = f"{i.get('quoteType')} has no company fundamentals. Use macro_context and the proxies instead."
        return out
    with _quiet():
        t = _yf().Ticker(symbol)
        try:
            q = t.quarterly_income_stmt
            if q is not None and not q.empty:
                rows = [r for r in ("Total Revenue", "Operating Income", "Net Income", "Diluted EPS") if r in q.index]
                qt = q.loc[rows].iloc[:, :5]
                out["quarterly"] = {str(c.date()): {r: _num(qt.at[r, c], 2) for r in rows} for c in qt.columns}
        except Exception:
            pass
        try:
            cal = t.calendar
            if isinstance(cal, dict) and cal.get("Earnings Date"):
                out["next_earnings"] = [str(d) for d in cal["Earnings Date"]]
        except Exception:
            pass
        try:
            ins = t.insider_transactions
            if ins is not None and not ins.empty:
                cols = [c for c in ("Start Date", "Insider", "Position", "Transaction", "Text", "Shares", "Value") if c in ins.columns]
                out["insider_transactions_recent"] = json.loads(ins[cols].head(8).to_json(orient="records", date_format="iso"))
        except Exception:
            pass
    return out


def _gnews(query: str, locale: str, as_of: date | None, days: int, limit: int) -> list[dict]:
    hl, gl = (locale.split(":") + ["US"])[:2]
    lang = hl.split("-")[0]
    q = query
    end = as_of or date.today()
    q += f" after:{(end - timedelta(days=days)).isoformat()} before:{(end + timedelta(days=1)).isoformat()}"
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": hl, "gl": gl, "ceid": f"{gl}:{lang}"})
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=12) as r:
        root = ET.fromstring(r.read())
    cutoff = datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc)
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        src = it.find("source")
        pub = it.findtext("pubDate")
        try:
            ts = parsedate_to_datetime(pub) if pub else None
        except (TypeError, ValueError):
            ts = None
        if ts and ts > cutoff:
            continue  # published after as_of: would be look-ahead
        items.append({"title": title, "source": src.text if src is not None else None, "published": ts.isoformat() if ts else None, "link": it.findtext("link")})
    items.sort(key=lambda x: x["published"] or "", reverse=True)
    seen, out = set(), []
    for x in items:
        key = x["title"].lower()[:80]
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out[:limit]


def news(query: str, locale: str = "en-US:US", as_of: date | None = None, days: int = 14, limit: int = 20) -> dict:
    try:
        items = _cached(("news", query, locale, as_of, days, limit), lambda: _gnews(query, locale, as_of, days, limit))
        return {"query": query, "locale": locale, "window_days": days, "as_of": str(as_of or date.today()), "items": items, "count": len(items)}
    except Exception as e:  # network or parse failure: report, never invent
        return {"query": query, "error": f"news fetch failed: {type(e).__name__}: {e}", "items": []}


def reddit_mentions(query: str, limit: int = 25) -> dict:
    """Public Reddit search, past week. Current only: not point-in-time."""
    url = "https://www.reddit.com/search.json?" + urllib.parse.urlencode({"q": query, "sort": "new", "t": "week", "limit": limit})
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        posts = [c["data"] for c in data.get("data", {}).get("children", [])]
        return {
            "point_in_time": False,
            "posts_last_week": len(posts),
            "total_score": int(sum(p.get("score", 0) for p in posts)),
            "top": [{"title": p.get("title"), "subreddit": p.get("subreddit"), "score": p.get("score"), "comments": p.get("num_comments")}
                    for p in sorted(posts, key=lambda p: -p.get("score", 0))[:10]],
        }
    except Exception as e:
        return {"point_in_time": False, "error": f"reddit fetch failed: {type(e).__name__}"}


def options_positioning(symbol: str) -> dict | None:
    """Put/call volume and open interest over the two nearest expiries. Current only."""
    with _quiet():
        try:
            t = _yf().Ticker(symbol)
            exps = list(t.options or [])[:2]
            if not exps:
                return None
            cv = pv = coi = poi = 0.0
            for e in exps:
                ch = t.option_chain(e)
                cv += float(ch.calls["volume"].fillna(0).sum())
                pv += float(ch.puts["volume"].fillna(0).sum())
                coi += float(ch.calls["openInterest"].fillna(0).sum())
                poi += float(ch.puts["openInterest"].fillna(0).sum())
        except Exception:
            return None
    return {
        "point_in_time": False,
        "expiries": exps,
        "put_call_volume_ratio": round(pv / cv, 3) if cv else None,
        "put_call_oi_ratio": round(poi / coi, 3) if coi else None,
    }


def analyst_trend(symbol: str) -> list[dict] | None:
    with _quiet():
        try:
            r = _yf().Ticker(symbol).recommendations
        except Exception:
            return None
    if r is None or getattr(r, "empty", True):
        return None
    return json.loads(r.head(4).to_json(orient="records"))


def screen(region: str, exchanges: tuple[str, ...], pages: int = 1, sector: str | None = None) -> list[dict]:
    """Up to pages x 250 listings on the given exchanges, largest market cap first, from
    Yahoo's screener. Several pages matter on venues crowded with foreign cross-listings."""

    def fetch():
        from yfinance import EquityQuery as Q

        exch = Q("eq", ["exchange", exchanges[0]]) if len(exchanges) == 1 else Q("or", [Q("eq", ["exchange", e]) for e in exchanges])
        parts = [Q("eq", ["region", region]), exch]
        if sector:
            parts.append(Q("eq", ["sector", sector]))
        out: list[dict] = []
        for page in range(pages):
            with _quiet():
                res = _yf().screen(Q("and", parts), sortField="intradaymarketcap", sortAsc=False, size=250, offset=page * 250)
            quotes = res.get("quotes", []) if isinstance(res, dict) else []
            out += quotes
            if len(quotes) < 250:
                break
        return out

    return _cached(("screen", region, exchanges, pages, sector), fetch)


def intraday_bars(symbols: list[str], period: str = "60d", interval: str = "5m", tz: str | None = None) -> dict[str, pd.DataFrame]:
    """5-minute OHLCV per symbol in exchange-local time. Cached for 5 minutes, not 15:
    intraday data goes stale fast."""
    key = ("intraday", tuple(symbols), period, interval)
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    with _quiet():
        raw = _yf().download(list(symbols), period=period, interval=interval, group_by="ticker",
                             auto_adjust=False, progress=False, threads=True)
    out: dict[str, pd.DataFrame] = {}
    if raw is not None and not raw.empty:
        for s in symbols:
            if isinstance(raw.columns, pd.MultiIndex):
                if s not in raw.columns.get_level_values(0):
                    continue
                df = raw[s]
            else:
                df = raw
            df = df[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
            if df.empty:
                continue
            if tz and df.index.tz is not None:
                df = df.tz_convert(tz)
            out[s] = df
    _CACHE[key] = (time.time(), out)
    return out
