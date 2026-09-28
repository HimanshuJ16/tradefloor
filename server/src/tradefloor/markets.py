"""Market registry and symbol resolution.

Yahoo Finance symbols are the common currency: one exchange suffix per venue, a caret
prefix for indices, =X for FX, =F for futures, -USD for crypto. Everything here is pure
data and pure functions so it can be tested offline. Online lookup (yfinance Search) is
done by the server only when the local rules cannot resolve a query.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Exchange:
    code: str
    name: str
    country: str
    suffix: str
    currency: str
    tz: str
    benchmark: str | None
    vol_index: str | None = None
    fx_vs_usd: str | None = None  # Yahoo symbol quoting local currency per USD
    news_locale: str = "en-US:US"  # hl:gl for Google News
    price_unit_note: str | None = None
    trading_days: int = 252


# Benchmarks and vol indices are the Yahoo symbols as of the date in docs/markets.md.
# scripts/check_markets.py fetches each one; run it before editing this table.
EXCHANGES: dict[str, Exchange] = {
    e.code: e
    for e in [
        Exchange("US", "NYSE / Nasdaq", "United States", "", "USD", "America/New_York", "^GSPC", "^VIX", None, "en-US:US"),
        Exchange("NSE", "National Stock Exchange of India", "India", ".NS", "INR", "Asia/Kolkata", "^NSEI", "^INDIAVIX", "INR=X", "en-IN:IN"),
        Exchange("BSE", "BSE India", "India", ".BO", "INR", "Asia/Kolkata", "^BSESN", "^INDIAVIX", "INR=X", "en-IN:IN"),
        Exchange("LSE", "London Stock Exchange", "United Kingdom", ".L", "GBP", "Europe/London", "^FTSE", None, "GBP=X", "en-GB:GB", "Most LSE equities are quoted in pence (GBp), not pounds."),
        Exchange("XETRA", "Deutsche Boerse Xetra", "Germany", ".DE", "EUR", "Europe/Berlin", "^GDAXI", None, "EUR=X", "en-DE:DE"),
        Exchange("FRA", "Frankfurt Stock Exchange", "Germany", ".F", "EUR", "Europe/Berlin", "^GDAXI", None, "EUR=X", "en-DE:DE"),
        Exchange("EPA", "Euronext Paris", "France", ".PA", "EUR", "Europe/Paris", "^FCHI", None, "EUR=X", "en-FR:FR"),
        Exchange("AMS", "Euronext Amsterdam", "Netherlands", ".AS", "EUR", "Europe/Amsterdam", "^AEX", None, "EUR=X", "en-NL:NL"),
        Exchange("EBR", "Euronext Brussels", "Belgium", ".BR", "EUR", "Europe/Brussels", "^BFX", None, "EUR=X", "en-BE:BE"),
        Exchange("BIT", "Borsa Italiana", "Italy", ".MI", "EUR", "Europe/Rome", "FTSEMIB.MI", None, "EUR=X", "en-IT:IT"),
        Exchange("BME", "Bolsa de Madrid", "Spain", ".MC", "EUR", "Europe/Madrid", "^IBEX", None, "EUR=X", "en-ES:ES"),
        Exchange("SIX", "SIX Swiss Exchange", "Switzerland", ".SW", "CHF", "Europe/Zurich", "^SSMI", None, "CHF=X", "en-CH:CH"),
        Exchange("STO", "Nasdaq Stockholm", "Sweden", ".ST", "SEK", "Europe/Stockholm", "^OMX", None, "SEK=X", "en-SE:SE"),
        Exchange("OSL", "Oslo Bors", "Norway", ".OL", "NOK", "Europe/Oslo", "^STOXX50E", None, "NOK=X", "en-NO:NO"),
        Exchange("CPH", "Nasdaq Copenhagen", "Denmark", ".CO", "DKK", "Europe/Copenhagen", "^STOXX50E", None, "DKK=X", "en-DK:DK"),
        Exchange("HEL", "Nasdaq Helsinki", "Finland", ".HE", "EUR", "Europe/Helsinki", "^STOXX50E", None, "EUR=X", "en-FI:FI"),
        Exchange("TSE", "Tokyo Stock Exchange", "Japan", ".T", "JPY", "Asia/Tokyo", "^N225", None, "JPY=X", "en-JP:JP"),
        Exchange("HKEX", "Hong Kong Exchanges", "Hong Kong", ".HK", "HKD", "Asia/Hong_Kong", "^HSI", None, "HKD=X", "en-HK:HK"),
        Exchange("SSE", "Shanghai Stock Exchange", "China", ".SS", "CNY", "Asia/Shanghai", "000001.SS", None, "CNY=X", "en-CN:CN"),
        Exchange("SZSE", "Shenzhen Stock Exchange", "China", ".SZ", "CNY", "Asia/Shanghai", "399001.SZ", None, "CNY=X", "en-CN:CN"),
        Exchange("KRX", "Korea Exchange (KOSPI)", "South Korea", ".KS", "KRW", "Asia/Seoul", "^KS11", None, "KRW=X", "en-KR:KR"),
        Exchange("KOSDAQ", "Korea Exchange (KOSDAQ)", "South Korea", ".KQ", "KRW", "Asia/Seoul", "^KQ11", None, "KRW=X", "en-KR:KR"),
        Exchange("TWSE", "Taiwan Stock Exchange", "Taiwan", ".TW", "TWD", "Asia/Taipei", "^TWII", None, "TWD=X", "en-TW:TW"),
        Exchange("TPEX", "Taipei Exchange", "Taiwan", ".TWO", "TWD", "Asia/Taipei", "^TWII", None, "TWD=X", "en-TW:TW"),
        Exchange("SGX", "Singapore Exchange", "Singapore", ".SI", "SGD", "Asia/Singapore", "^STI", None, "SGD=X", "en-SG:SG"),
        Exchange("ASX", "Australian Securities Exchange", "Australia", ".AX", "AUD", "Australia/Sydney", "^AXJO", None, "AUD=X", "en-AU:AU"),
        Exchange("NZX", "New Zealand Exchange", "New Zealand", ".NZ", "NZD", "Pacific/Auckland", "^NZ50", None, "NZD=X", "en-NZ:NZ"),
        Exchange("TSX", "Toronto Stock Exchange", "Canada", ".TO", "CAD", "America/Toronto", "^GSPTSE", None, "CAD=X", "en-CA:CA"),
        Exchange("TSXV", "TSX Venture Exchange", "Canada", ".V", "CAD", "America/Toronto", "^GSPTSE", None, "CAD=X", "en-CA:CA"),
        Exchange("B3", "B3 Brasil Bolsa Balcao", "Brazil", ".SA", "BRL", "America/Sao_Paulo", "^BVSP", None, "BRL=X", "en-BR:BR"),
        Exchange("BMV", "Bolsa Mexicana de Valores", "Mexico", ".MX", "MXN", "America/Mexico_City", "^MXX", None, "MXN=X", "en-MX:MX"),
        Exchange("JSE", "Johannesburg Stock Exchange", "South Africa", ".JO", "ZAR", "Africa/Johannesburg", "^J203.JO", None, "ZAR=X", "en-ZA:ZA", "JSE equities are quoted in cents (ZAc), not rand."),
        Exchange("TADAWUL", "Saudi Exchange", "Saudi Arabia", ".SR", "SAR", "Asia/Riyadh", "^TASI.SR", None, "SAR=X", "en-SA:SA"),
        Exchange("TASE", "Tel Aviv Stock Exchange", "Israel", ".TA", "ILS", "Asia/Jerusalem", "^TA125.TA", None, "ILS=X", "en-IL:IL", "TASE equities are quoted in agorot (ILA), not shekels."),
        Exchange("IDX", "Indonesia Stock Exchange", "Indonesia", ".JK", "IDR", "Asia/Jakarta", "^JKSE", None, "IDR=X", "en-ID:ID"),
        Exchange("BURSA", "Bursa Malaysia", "Malaysia", ".KL", "MYR", "Asia/Kuala_Lumpur", "^KLSE", None, "MYR=X", "en-MY:MY"),
        Exchange("SET", "Stock Exchange of Thailand", "Thailand", ".BK", "THB", "Asia/Bangkok", "^SET.BK", None, "THB=X", "en-TH:TH"),
        Exchange("BIST", "Borsa Istanbul", "Turkey", ".IS", "TRY", "Europe/Istanbul", "XU100.IS", None, "TRY=X", "en-TR:TR"),
        Exchange("CRYPTO", "Crypto (spot, USD)", "Global", "-USD", "USD", "UTC", "BTC-USD", None, None, "en-US:US", None, 365),
        Exchange("FX", "Foreign exchange", "Global", "=X", "", "UTC", "DX-Y.NYB", None, None, "en-US:US", None, 260),
        Exchange("FUT", "Futures (continuous front month)", "Global", "=F", "USD", "America/New_York", "^GSPC", "^VIX", None, "en-US:US"),
    ]
}

# Longest suffix first so ".TWO" wins over ".TW".
_SUFFIXES = sorted(((e.suffix, e.code) for e in EXCHANGES.values() if e.suffix), key=lambda t: -len(t[0]))


@dataclass(frozen=True)
class IndexAlias:
    symbol: str
    name: str
    exchange: str
    proxies: tuple[str, ...] = field(default_factory=tuple)


# Friendly names people type. Proxies are tradeable instruments that track the index,
# because an index level itself cannot be bought.
INDEX_ALIASES: dict[str, IndexAlias] = {}


def _alias(names: list[str], symbol: str, name: str, exchange: str, proxies: tuple[str, ...] = ()) -> None:
    for n in names:
        INDEX_ALIASES[_norm(n)] = IndexAlias(symbol, name, exchange, proxies)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9&]+", "", s.lower())


_alias(["nifty", "nifty 50", "nifty50"], "^NSEI", "NIFTY 50", "NSE", ("NIFTYBEES.NS",))
_alias(["bank nifty", "banknifty", "nifty bank"], "^NSEBANK", "NIFTY Bank", "NSE", ("BANKBEES.NS",))
_alias(["sensex", "bse sensex"], "^BSESN", "S&P BSE SENSEX", "BSE", ())
_alias(["india vix", "indiavix"], "^INDIAVIX", "India VIX", "NSE", ())
_alias(["s&p 500", "sp500", "s&p", "spx", "sp 500"], "^GSPC", "S&P 500", "US", ("SPY", "VOO", "ES=F"))
_alias(["nasdaq 100", "nasdaq100", "ndx"], "^NDX", "Nasdaq 100", "US", ("QQQ", "NQ=F"))
_alias(["nasdaq", "nasdaq composite"], "^IXIC", "Nasdaq Composite", "US", ("ONEQ",))
_alias(["dow", "dow jones", "djia"], "^DJI", "Dow Jones Industrial Average", "US", ("DIA", "YM=F"))
_alias(["russell 2000", "russell2000", "rut"], "^RUT", "Russell 2000", "US", ("IWM", "RTY=F"))
_alias(["vix"], "^VIX", "CBOE Volatility Index", "US", ())
_alias(["ftse", "ftse 100", "ftse100"], "^FTSE", "FTSE 100", "LSE", ("ISF.L",))
_alias(["dax", "dax 40"], "^GDAXI", "DAX 40", "XETRA", ("EXS1.DE",))
_alias(["cac", "cac 40"], "^FCHI", "CAC 40", "EPA", ("CAC.PA",))
_alias(["euro stoxx 50", "eurostoxx", "stoxx 50", "sx5e"], "^STOXX50E", "EURO STOXX 50", "XETRA", ("FEZ",))
_alias(["aex"], "^AEX", "AEX", "AMS", ())
_alias(["ibex", "ibex 35"], "^IBEX", "IBEX 35", "BME", ())
_alias(["ftse mib", "mib"], "FTSEMIB.MI", "FTSE MIB", "BIT", ())
_alias(["smi", "swiss market index"], "^SSMI", "Swiss Market Index", "SIX", ())
_alias(["nikkei", "nikkei 225", "n225"], "^N225", "Nikkei 225", "TSE", ("1321.T", "EWJ"))
_alias(["hang seng", "hsi"], "^HSI", "Hang Seng", "HKEX", ("2800.HK",))
_alias(["shanghai composite", "sse composite"], "000001.SS", "SSE Composite", "SSE", ())
_alias(["csi 300", "csi300"], "000300.SS", "CSI 300", "SSE", ("ASHR",))
_alias(["kospi"], "^KS11", "KOSPI", "KRX", ("EWY",))
_alias(["taiex", "twse"], "^TWII", "TAIEX", "TWSE", ("0050.TW", "EWT"))
_alias(["sti", "straits times"], "^STI", "Straits Times Index", "SGX", ("ES3.SI",))
_alias(["asx 200", "asx200", "xjo"], "^AXJO", "S&P/ASX 200", "ASX", ("STW.AX",))
_alias(["tsx", "s&p tsx"], "^GSPTSE", "S&P/TSX Composite", "TSX", ("XIU.TO",))
_alias(["ibovespa", "bovespa"], "^BVSP", "Ibovespa", "B3", ("BOVA11.SA", "EWZ"))
_alias(["ipc", "mexbol"], "^MXX", "S&P/BMV IPC", "BMV", ("EWW",))
_alias(["gold"], "GC=F", "Gold futures", "FUT", ("GLD",))
_alias(["silver"], "SI=F", "Silver futures", "FUT", ("SLV",))
_alias(["crude", "wti", "crude oil"], "CL=F", "WTI crude futures", "FUT", ("USO",))
_alias(["brent"], "BZ=F", "Brent crude futures", "FUT", ("BNO",))
_alias(["bitcoin", "btc"], "BTC-USD", "Bitcoin", "CRYPTO", ())
_alias(["ethereum", "eth"], "ETH-USD", "Ethereum", "CRYPTO", ())
_alias(["dxy", "dollar index"], "DX-Y.NYB", "US Dollar Index", "FX", ("UUP",))
_alias(["us 10y", "us10y", "tnx"], "^TNX", "US 10Y Treasury yield (x10)", "US", ())


@dataclass
class Resolution:
    symbol: str
    exchange: str
    kind: str  # equity | index | fx | future | crypto
    name: str | None = None
    proxies: list[str] = field(default_factory=list)
    note: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        ex = EXCHANGES[self.exchange]
        d["currency"] = ex.currency
        d["timezone"] = ex.tz
        d["benchmark"] = ex.benchmark
        d["vol_index"] = ex.vol_index
        d["trading_days_per_year"] = ex.trading_days
        if ex.price_unit_note and self.kind == "equity":
            d["price_unit_note"] = ex.price_unit_note
        return d


def exchange_for_symbol(symbol: str) -> str:
    s = symbol.upper()
    if s.endswith("=X"):
        return "FX"
    if s.endswith("=F"):
        return "FUT"
    if re.fullmatch(r"[A-Z0-9]+-(USD|USDT|EUR|INR)", s):
        return "CRYPTO"
    for suffix, code in _SUFFIXES:
        if suffix.startswith(".") and s.endswith(suffix.upper()):
            return code
    if s.startswith("^"):
        for a in INDEX_ALIASES.values():
            if a.symbol == s:
                return a.exchange
        for e in EXCHANGES.values():
            if e.benchmark == s or e.vol_index == s:
                return e.code
    return "US"


def kind_for_symbol(symbol: str) -> str:
    s = symbol.upper()
    if s.endswith("=X"):
        return "fx"
    if s.endswith("=F"):
        return "future"
    if exchange_for_symbol(s) == "CRYPTO":
        return "crypto"
    if s.startswith("^") or any(a.symbol == s for a in INDEX_ALIASES.values()):
        return "index"
    return "equity"


def resolve_local(query: str, default_market: str = "US") -> Resolution | None:
    """Resolve without the network. Returns None when a lookup is needed."""
    q = query.strip()
    if not q:
        return None
    alias = INDEX_ALIASES.get(_norm(q))
    if alias:
        kind = kind_for_symbol(alias.symbol)
        return Resolution(alias.symbol, alias.exchange, kind, alias.name, list(alias.proxies))

    # "NSE:RELIANCE" / "RELIANCE:NSE" exchange-prefixed forms, as TradingView writes them.
    m = re.fullmatch(r"([A-Za-z0-9]+):([A-Za-z0-9.\-&]+)", q) or re.fullmatch(r"([A-Za-z0-9.\-&]+):([A-Za-z0-9]+)", q)
    if m:
        a, b = m.group(1).upper(), m.group(2).upper()
        code, tick = (a, b) if a in EXCHANGES else (b, a) if b in EXCHANGES else (None, None)
        if code:
            return Resolution(tick + EXCHANGES[code].suffix, code, "equity")

    looks_like_symbol = re.fullmatch(r"\^?[A-Za-z0-9.\-=&]{1,20}", q) is not None
    if not looks_like_symbol:
        return None
    s = q.upper()
    if s.startswith("^") or s.endswith(("=X", "=F")) or "-" in s or any(s.endswith(sfx.upper()) for sfx, _ in _SUFFIXES if sfx.startswith(".")):
        code = exchange_for_symbol(s)
        return Resolution(s, code, kind_for_symbol(s))

    # A bare ticker. Attach the user's home market suffix; flag it so the caller can confirm.
    market = default_market.upper() if default_market.upper() in EXCHANGES else "US"
    ex = EXCHANGES[market]
    if market in ("CRYPTO", "FX", "FUT"):
        market, ex = "US", EXCHANGES["US"]
    note = None if market == "US" else f"Bare ticker; assumed home market {market}. Pass an explicit suffix if wrong."
    return Resolution(s + ex.suffix, market, "equity", note=note)


def list_markets() -> list[dict]:
    return [
        {"code": e.code, "name": e.name, "country": e.country, "suffix": e.suffix, "currency": e.currency, "benchmark": e.benchmark}
        for e in EXCHANGES.values()
    ]


def horizon_to_days(horizon: str | int, trading_days_per_year: int = 252) -> int:
    """'1d', '2w', '1m', '3m', '1y' or an int count of trading days."""
    if isinstance(horizon, int):
        return max(1, horizon)
    h = str(horizon).strip().lower()
    if h.isdigit():
        return max(1, int(h))
    m = re.fullmatch(r"(\d+)\s*(d|day|days|w|wk|week|weeks|m|mo|month|months|q|y|yr|year|years)", h)
    if not m:
        raise ValueError(f"Cannot parse horizon {horizon!r}. Use e.g. 1d, 1w, 1m, 3m, 1y.")
    n, unit = int(m.group(1)), m.group(2)
    per_week = 7 if trading_days_per_year >= 365 else 5
    per_month = round(trading_days_per_year / 12)
    days = {
        "d": n, "day": n, "days": n,
        "w": n * per_week, "wk": n * per_week, "week": n * per_week, "weeks": n * per_week,
        "m": n * per_month, "mo": n * per_month, "month": n * per_month, "months": n * per_month,
        "q": n * per_month * 3,
        "y": n * trading_days_per_year, "yr": n * trading_days_per_year, "year": n * trading_days_per_year, "years": n * trading_days_per_year,
    }[unit]
    return max(1, days)
