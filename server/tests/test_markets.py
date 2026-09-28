import pytest

from tradefloor import markets as m


@pytest.mark.parametrize(
    "query,symbol,exchange,kind",
    [
        ("nifty 50", "^NSEI", "NSE", "index"),
        ("NIFTY", "^NSEI", "NSE", "index"),
        ("S&P 500", "^GSPC", "US", "index"),
        ("dax", "^GDAXI", "XETRA", "index"),
        ("bank nifty", "^NSEBANK", "NSE", "index"),
        ("gold", "GC=F", "FUT", "future"),
        ("bitcoin", "BTC-USD", "CRYPTO", "crypto"),
        ("7203.T", "7203.T", "TSE", "equity"),
        ("RELIANCE.NS", "RELIANCE.NS", "NSE", "equity"),
        ("6488.TWO", "6488.TWO", "TPEX", "equity"),
        ("2330.TW", "2330.TW", "TWSE", "equity"),
        ("NSE:RELIANCE", "RELIANCE.NS", "NSE", "equity"),
        ("VOD:LSE", "VOD.L", "LSE", "equity"),
        ("EURUSD=X", "EURUSD=X", "FX", "fx"),
        ("BRK-B", "BRK-B", "US", "equity"),
        ("^N225", "^N225", "TSE", "index"),
    ],
)
def test_resolve_local(query, symbol, exchange, kind):
    r = m.resolve_local(query)
    assert r is not None
    assert (r.symbol, r.exchange, r.kind) == (symbol, exchange, kind)


def test_bare_ticker_uses_home_market():
    r = m.resolve_local("INFY", "NSE")
    assert r.symbol == "INFY.NS" and r.exchange == "NSE" and r.note
    us = m.resolve_local("AAPL", "US")
    assert us.symbol == "AAPL" and us.note is None


def test_free_text_needs_lookup():
    assert m.resolve_local("reliance industries limited") is None


def test_index_carries_proxies():
    d = m.resolve_local("s&p 500").to_dict()
    assert "SPY" in d["proxies"] and d["currency"] == "USD" and d["benchmark"] == "^GSPC"


def test_pence_note_on_lse_equity():
    assert "pence" in m.resolve_local("VOD.L").to_dict()["price_unit_note"]


@pytest.mark.parametrize("h,days", [("1d", 1), ("1w", 5), ("2w", 10), ("1m", 21), ("3m", 63), ("1y", 252), (15, 15), ("15", 15)])
def test_horizon(h, days):
    assert m.horizon_to_days(h) == days


def test_horizon_crypto_calendar():
    assert m.horizon_to_days("1w", 365) == 7


def test_horizon_bad():
    with pytest.raises(ValueError):
        m.horizon_to_days("soon")


def test_every_exchange_has_currency_and_tz():
    for e in m.EXCHANGES.values():
        assert e.tz and (e.currency or e.code == "FX")
