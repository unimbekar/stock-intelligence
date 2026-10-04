"""Average-cost ledger for paper positions.

Buys add to cost basis, including fees. Sells realize (price - average) × shares,
minus fees. Shorts are stored as negative quantity. A fill that would cross through
zero is rejected so an opening and a closing trade stay separate rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Fill:
    ticker: str
    side: str
    quantity: Decimal
    price: Decimal
    fees: Decimal = Decimal("0")


@dataclass
class Position:
    ticker: str
    quantity: Decimal
    average_cost: Decimal
    cost_basis: Decimal
    realized_pnl: Decimal


def unrealized_pnl(position: Position, mark: Decimal) -> Decimal:
    if position.quantity > 0:
        return (mark - position.average_cost) * position.quantity
    if position.quantity < 0:
        return (position.average_cost - mark) * abs(position.quantity)
    return Decimal("0")


def apply_fills(fills: list[Fill]) -> dict[str, Position]:
    book: dict[str, Position] = {}
    for fill in fills:
        _apply(book, fill)
    return book


def _apply(book: dict[str, Position], fill: Fill) -> None:
    ticker = fill.ticker.upper()
    if fill.quantity <= 0:
        raise ValueError("quantity must be positive")
    if fill.price <= 0:
        raise ValueError("price must be positive")
    if fill.fees < 0:
        raise ValueError("fees cannot be negative")
    if fill.side not in {"buy", "sell", "short", "cover"}:
        raise ValueError(f"unsupported side {fill.side}")

    position = book.get(ticker) or Position(
        ticker=ticker,
        quantity=Decimal("0"),
        average_cost=Decimal("0"),
        cost_basis=Decimal("0"),
        realized_pnl=Decimal("0"),
    )

    if fill.side == "buy":
        if position.quantity < 0:
            raise ValueError(f"{ticker} is short; cover before buying")
        cost = position.cost_basis + fill.quantity * fill.price + fill.fees
        quantity = position.quantity + fill.quantity
        position.quantity = quantity
        position.cost_basis = cost
        position.average_cost = cost / quantity
    elif fill.side == "sell":
        if position.quantity <= 0:
            raise ValueError(f"{ticker} has no long position to sell")
        if fill.quantity > position.quantity:
            raise ValueError(f"{ticker} sell quantity exceeds the open position")
        position.realized_pnl += (fill.price - position.average_cost) * fill.quantity - fill.fees
        position.quantity -= fill.quantity
        position.cost_basis = position.average_cost * position.quantity
        if position.quantity == 0:
            position.average_cost = Decimal("0")
            position.cost_basis = Decimal("0")
    elif fill.side == "short":
        if position.quantity > 0:
            raise ValueError(f"{ticker} is long; sell before shorting")
        proceeds = abs(position.cost_basis) + fill.quantity * fill.price - fill.fees
        quantity = position.quantity - fill.quantity
        position.quantity = quantity
        position.cost_basis = -proceeds
        position.average_cost = proceeds / abs(quantity)
    else:
        if position.quantity >= 0:
            raise ValueError(f"{ticker} has no short position to cover")
        if fill.quantity > abs(position.quantity):
            raise ValueError(f"{ticker} cover quantity exceeds the open short")
        position.realized_pnl += (position.average_cost - fill.price) * fill.quantity - fill.fees
        position.quantity += fill.quantity
        position.cost_basis = -(position.average_cost * abs(position.quantity))
        if position.quantity == 0:
            position.average_cost = Decimal("0")
            position.cost_basis = Decimal("0")

    book[ticker] = position
