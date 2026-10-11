import pytest
from tradefloor.microstructure import Book, Trader, simulate


def test_price_time_priority_partial_fill_and_reservation_release():
    book = Book(
        {"buyer": Trader(1000, 0), "seller1": Trader(0, 10), "seller2": Trader(0, 10)}
    )
    a = book.submit("seller1", "sell", 10, 6)
    b = book.submit("seller2", "sell", 10, 6)
    book.submit("buyer", "buy", 12, 8)
    assert [t["maker_order"] for t in book.trades] == [a["id"], b["id"]]
    assert [t["quantity"] for t in book.trades] == [6, 2]
    assert book.traders["buyer"].cash == 920 and book.traders["buyer"].inventory == 8
    assert book.traders["buyer"].reserved_cash == 0
    assert book.traders["seller2"].reserved_inventory == 4
    book.cancel("seller2")
    assert book.traders["seller2"].reserved_inventory == 0
    book.check()


def test_pending_orders_cannot_double_spend_or_oversell():
    book = Book({"a": Trader(100, 10), "b": Trader(100, 10)})
    book.submit("a", "buy", 10, 10)
    with pytest.raises(ValueError, match="budget|cash"):
        book.submit("a", "buy", 10, 1)
    book.submit("b", "sell", 12, 10)
    with pytest.raises(ValueError):
        book.submit("b", "sell", 12, 1)
    book.cancel("a")
    book.submit("a", "buy", 12, 8)
    book.check()


def test_best_price_first_and_no_self_trades():
    book = Book({"a": Trader(1000, 10), "b": Trader(1000, 10), "c": Trader(1000, 10)})
    book.submit("b", "sell", 11, 2)
    book.submit("c", "sell", 10, 2)
    book.submit("a", "buy", 12, 3)
    assert [t["price"] for t in book.trades] == [10, 11]
    assert all(t["buyer"] != t["seller"] for t in book.trades)


@pytest.mark.parametrize("liquidity", [0.05, 1, 10])
def test_seeded_market_ledger_conserves_cash_and_inventory(liquidity):
    args = {
        "steps": 30,
        "liquidity": liquidity,
        "reactions": [{"group": "retail", "sentiment": -0.8, "conviction": 0.7}],
    }
    a, b = simulate(**args), simulate(**args)
    assert a == b
    assert a["conservation"]["cash"] == pytest.approx(a["conservation"]["initial_cash"])
    assert a["conservation"]["inventory"] == pytest.approx(
        a["conservation"]["initial_inventory"]
    )
    assert all(min(t["cash"], t["inventory"]) >= 0 for t in a["participants"].values())
