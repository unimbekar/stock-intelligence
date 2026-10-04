"""Portfolio marks, cash, equity curve, and concentration."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from decimal import Decimal

from meridian_analytics.ledger import Fill, apply_fills, unrealized_pnl


def cash_delta(side: str, quantity: Decimal, price: Decimal, fees: Decimal) -> Decimal:
    notion = quantity * price
    if side in {"buy", "cover"}:
        return -(notion + fees)
    if side in {"sell", "short"}:
        return notion - fees
    raise ValueError(f"unsupported side {side}")


def opening_cash(current_cash: Decimal, fills: list[Fill]) -> Decimal:
    spent = sum((cash_delta(fill.side, fill.quantity, fill.price, fill.fees) for fill in fills), Decimal("0"))
    return current_cash - spent


def closing_pnls(fills: list[Fill]) -> list[Decimal]:
    realized: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    pnls: list[Decimal] = []
    applied: list[Fill] = []
    for fill in fills:
        before = realized[fill.ticker.upper()]
        applied.append(fill)
        book = apply_fills(applied)
        after = book[fill.ticker.upper()].realized_pnl
        realized[fill.ticker.upper()] = after
        if after != before:
            pnls.append(after - before)
    return pnls


def holding_rating(
    *,
    price: float,
    sma20: float | None,
    sma50: float | None,
    rsi: float | None,
    eps_growth: float | None,
    revenue_growth: float | None,
    pe: float | None,
) -> str:
    """Buy, hold, or sell from the last close and filed fundamentals.

    This is a local rule. It is not a broker rating and it does not use an analyst feed.
    """
    supportive = 0
    weak = 0
    if sma50 is not None:
        supportive += price > sma50
        weak += price < sma50
    if sma20 is not None:
        supportive += price > sma20
        weak += price < sma20
    if eps_growth is not None:
        supportive += eps_growth > 0
        weak += eps_growth < 0
    if revenue_growth is not None:
        supportive += revenue_growth > 0.05
        weak += revenue_growth < 0
    if rsi is not None:
        supportive += 45 <= rsi <= 70
        weak += rsi >= 75 or rsi <= 35
    if pe is not None and pe > 0:
        supportive += pe < 25
        weak += pe > 50
    if supportive >= 3 and supportive > weak:
        return "Buy"
    if weak >= 3 and weak > supportive:
        return "Sell"
    return "Hold"


def position_view(
    fills: list[Fill],
    marks: dict[str, tuple[Decimal, Decimal, str]],
) -> list[dict[str, Decimal | str]]:
    """marks: ticker -> (price, previous, sector)."""
    book = apply_fills(fills)
    rows: list[dict[str, Decimal | str]] = []
    for ticker, position in book.items():
        if position.quantity == 0 or ticker not in marks:
            continue
        price, previous, sector = marks[ticker]
        rows.append(
            {
                "ticker": ticker,
                "quantity": position.quantity,
                "average_cost": position.average_cost,
                "cost_basis": position.cost_basis,
                "price": price,
                "market_value": position.quantity * price,
                "unrealized_pnl": unrealized_pnl(position, price),
                "daily_pnl": position.quantity * (price - previous),
                "realized_pnl": position.realized_pnl,
                "sector": sector,
            }
        )
    return rows


def equity_curve(
    fills: list[tuple[date, Fill]],
    current_cash: Decimal,
    closes: dict[str, dict[date, Decimal]],
) -> list[tuple[date, Decimal]]:
    ordered = sorted(fills, key=lambda item: item[0])
    start_cash = opening_cash(current_cash, [fill for _day, fill in ordered])
    sessions = sorted({day for series in closes.values() for day in series})
    if ordered:
        sessions = [day for day in sessions if day >= ordered[0][0]]
    curve: list[tuple[date, Decimal]] = []
    for session in sessions:
        used = [fill for day, fill in ordered if day <= session]
        cash = start_cash + sum(
            (cash_delta(fill.side, fill.quantity, fill.price, fill.fees) for fill in used),
            Decimal("0"),
        )
        book = apply_fills(used) if used else {}
        marked = Decimal("0")
        for ticker, position in book.items():
            series = closes.get(ticker, {})
            price = _price_on_or_before(series, session)
            if price is None or position.quantity == 0:
                continue
            marked += position.quantity * price
        curve.append((session, cash + marked))
    return curve


def _price_on_or_before(series: dict[date, Decimal], session: date) -> Decimal | None:
    candidates = [day for day in series if day <= session]
    if not candidates:
        return None
    return series[max(candidates)]


def pearson(left: list[float], right: list[float]) -> float | None:
    count = min(len(left), len(right))
    if count < 3:
        return None
    xs = left[-count:]
    ys = right[-count:]
    mean_x = sum(xs) / count
    mean_y = sum(ys) / count
    numer = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return None
    return numer / (den_x * den_y)
