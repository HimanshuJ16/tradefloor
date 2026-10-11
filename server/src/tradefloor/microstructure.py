"""Experimental price-time limit order book with cash/inventory constraints.

This is a synthetic market-mechanics sandbox, not a calibrated exchange simulator.
It is separate from the behavioral return model so constraints are never implied there.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
from . import swarm, validation


@dataclass
class Trader:
    cash: float
    inventory: float
    reserved_cash: float = 0
    reserved_inventory: float = 0


class Book:
    def __init__(self, traders: dict[str, Trader]):
        self.traders = traders
        self.orders: list[dict] = []
        self.trades: list[dict] = []
        self.sequence = 0
        self.initial_cash = sum(t.cash for t in traders.values())
        self.initial_inventory = sum(t.inventory for t in traders.values())
        self.check()

    def check(self):
        if not math.isclose(
            sum(t.cash for t in self.traders.values()), self.initial_cash, abs_tol=1e-6
        ):
            raise RuntimeError("cash conservation violated")
        if not math.isclose(
            sum(t.inventory for t in self.traders.values()),
            self.initial_inventory,
            abs_tol=1e-8,
        ):
            raise RuntimeError("inventory conservation violated")
        for t in self.traders.values():
            if (
                min(t.cash, t.inventory, t.reserved_cash, t.reserved_inventory) < -1e-7
                or t.reserved_cash > t.cash + 1e-7
                or t.reserved_inventory > t.inventory + 1e-7
            ):
                raise RuntimeError("participant budget violated")

    def cancel(self, owner: str):
        keep = []
        for o in self.orders:
            if o["owner"] != owner:
                keep.append(o)
            else:
                trader = self.traders[owner]
                if o["side"] == "buy":
                    trader.reserved_cash -= o["limit"] * o["remaining"]
                else:
                    trader.reserved_inventory -= o["remaining"]
        self.orders = keep
        self.check()

    def submit(self, owner: str, side: str, limit: float, quantity: float):
        if owner not in self.traders or side not in ("buy", "sell"):
            raise ValueError("unknown trader or side")
        limit = validation.number(limit, "limit", 1e-8, 1e9)
        quantity = validation.number(quantity, "quantity", 1e-8, 1e9)
        t = self.traders[owner]
        budget = (
            (t.cash - t.reserved_cash) / limit
            if side == "buy"
            else t.inventory - t.reserved_inventory
        )
        if quantity > budget + 1e-8:
            raise ValueError("order exceeds available cash/inventory")
        self.sequence += 1
        incoming = {
            "id": self.sequence,
            "owner": owner,
            "side": side,
            "limit": limit,
            "remaining": quantity,
        }
        if side == "buy":
            t.reserved_cash += quantity * limit
        else:
            t.reserved_inventory += quantity
        eligible = [
            o
            for o in self.orders
            if o["owner"] != owner
            and o["side"] != side
            and (o["limit"] <= limit if side == "buy" else o["limit"] >= limit)
        ]
        eligible.sort(
            key=lambda o: (o["limit"] if side == "buy" else -o["limit"], o["id"])
        )
        for resting in eligible:
            q = min(incoming["remaining"], resting["remaining"])
            if q <= 1e-10:
                break
            price = resting["limit"]
            buy, sell = (incoming, resting) if side == "buy" else (resting, incoming)
            buyer, seller = self.traders[buy["owner"]], self.traders[sell["owner"]]
            buyer.reserved_cash -= q * buy["limit"]
            seller.reserved_inventory -= q
            buyer.cash -= q * price
            seller.cash += q * price
            buyer.inventory += q
            seller.inventory -= q
            incoming["remaining"] -= q
            resting["remaining"] -= q
            self.trades.append(
                {
                    "taker_order": incoming["id"],
                    "maker_order": resting["id"],
                    "buyer": buy["owner"],
                    "seller": sell["owner"],
                    "price": price,
                    "quantity": q,
                }
            )
        self.orders = [o for o in self.orders if o["remaining"] > 1e-9]
        if incoming["remaining"] > 1e-9:
            self.orders.append(incoming)
        self.check()
        return incoming

    def quotes(self):
        bid = max((o["limit"] for o in self.orders if o["side"] == "buy"), default=None)
        ask = min(
            (o["limit"] for o in self.orders if o["side"] == "sell"), default=None
        )
        return {
            "bid": bid,
            "ask": ask,
            "spread": None if bid is None or ask is None else ask - bid,
        }


def simulate(
    steps: int = 120,
    seed: int = 7,
    reactions: list[dict] | None = None,
    liquidity: float = 1,
    persistence: float = 20,
) -> dict:
    steps = validation.integer(steps, "steps", 10, 1000)
    seed = validation.integer(seed, "seed", 0, 2**32 - 1)
    liquidity = validation.number(liquidity, "liquidity", 0.05, 10)
    persistence = validation.number(persistence, "persistence", 0.5, 1000)
    groups = swarm.roster("US")
    parsed = {}
    for raw in reactions or []:
        r = swarm.Reaction.parse(raw)
        if r.group not in {g.id for g in groups} or r.group in parsed:
            raise ValueError("reactions need unique known US roster groups")
        parsed[r.group] = r
    initial = {g.id: Trader(10000 * liquidity, 100 * liquidity) for g in groups}
    book = Book(initial)
    rng = np.random.default_rng(seed)
    tape = []
    last = 100.0
    submitted = 0
    for step in range(steps):
        # Each participant refreshes its quotes; cancellation releases its reserved funds.
        for index in rng.permutation(len(groups)):
            g = groups[int(index)]
            book.cancel(g.id)
            t = book.traders[g.id]
            r = parsed.get(g.id)
            reaction = (
                0
                if r is None
                else r.sentiment
                * r.conviction
                * math.exp(-math.log(2) * step / persistence)
            )
            anchor = 100 + (last - 100) * g.k_trend + reaction * 3 * g.k_news
            anchor = max(1, anchor + rng.normal(0, 0.35))
            spread = 0.3 + (1 / liquidity) * 0.2
            for side, price in (
                ("buy", anchor - spread / 2),
                ("sell", anchor + spread / 2),
            ):
                budget = (
                    (t.cash - t.reserved_cash) / price
                    if side == "buy"
                    else t.inventory - t.reserved_inventory
                )
                qty = min(float(rng.integers(1, 11)) * liquidity, max(0, budget))
                if qty > 1e-8:
                    book.submit(g.id, side, price, qty)
                    submitted += 1
        if book.trades:
            last = book.trades[-1]["price"]
        tape.append(
            {
                "step": step + 1,
                "last": last,
                **book.quotes(),
                "executions": len(book.trades),
            }
        )
    return {
        "model": "experimental constrained limit-order-book-v1",
        "seed": seed,
        "steps": steps,
        "last_price": last,
        "return_pct": (last / 100 - 1) * 100,
        "submitted_orders": submitted,
        "executions": len(book.trades),
        "tape": tape,
        "trades": book.trades,
        "participants": {
            key: {
                "cash": t.cash,
                "inventory": t.inventory,
                "reserved_cash": t.reserved_cash,
                "reserved_inventory": t.reserved_inventory,
                "marked_value": t.cash + t.inventory * last,
            }
            for key, t in book.traders.items()
        },
        "conservation": {
            "cash": sum(t.cash for t in book.traders.values()),
            "inventory": sum(t.inventory for t in book.traders.values()),
            "initial_cash": book.initial_cash,
            "initial_inventory": book.initial_inventory,
        },
        "assumptions": "Synthetic single asset, limit-only orders, price-time priority, no self trades, no borrowing/shorting, no fees, arbitrary behavioral scale. Not calibrated to an exchange.",
        "research_question": "How do cash/inventory constraints and thinner liquidity change the path under these supplied reactions?",
        "forecast_status": "No probability forecast or demonstrated trading edge",
    }
