from __future__ import annotations

import math
from datetime import date
from decimal import Decimal

from meridian_analytics.scoring import IdeaFilters, ScoreInput, composite, rank, reasons
from meridian_research.providers import MockAnalystProvider, bundle_for
from meridian_trading.sizing import plan_position

STYLE_ATR = {
    "day": (Decimal("0.6"), Decimal("1"), Decimal("1.5")),
    "swing": (Decimal("1.5"), Decimal("2"), Decimal("3")),
    "short": (Decimal("2"), Decimal("2"), Decimal("3")),
    "long": (Decimal("3"), Decimal("3"), Decimal("5")),
}
RISK_PERCENT = {
    "conservative": Decimal("0.5"),
    "moderate": Decimal("1"),
    "aggressive": Decimal("2"),
}


def build_inputs(book) -> list[ScoreInput]:
    sector_moves: dict[str, list[float]] = {}
    prepared: list[tuple] = []
    live = getattr(book, "data_mode", "mock") == "live"
    analyst = None if live else MockAnalystProvider(book)
    for quote in book.quotes():
        bars = book.bars(quote.ticker)
        technicals = book.technicals(quote.ticker)
        fundamentals = book.fundamentals(quote.ticker)
        if len(bars) >= 21:
            move = float((bars[-1].close - bars[-21].close) / bars[-21].close)
            sector_moves.setdefault(quote.sector, []).append(move)
        label = None if analyst is None else analyst.get_analyst_ratings(quote.ticker).consensus
        prepared.append((quote, technicals, fundamentals, bars, label))
    sector_mean = {name: sum(values) / len(values) for name, values in sector_moves.items()}
    rows: list[ScoreInput] = []
    for quote, technicals, fundamentals, bars, consensus in prepared:
        rows.append(
            ScoreInput(
                ticker=quote.ticker,
                company=quote.name,
                price=float(quote.price),
                market_cap=quote.market_cap,
                volume=quote.volume,
                sector=quote.sector,
                categories=tuple(quote.categories),
                rsi=technicals.rsi,
                sma20=technicals.sma20,
                sma50=technicals.sma50,
                sma200=technicals.sma200,
                relative_volume=technicals.relative_volume,
                atr=technicals.atr,
                annualized_vol=_volatility(bars),
                revenue_growth=fundamentals.revenue_growth,
                eps_growth=fundamentals.eps_growth,
                operating_margin=fundamentals.operating_margin,
                roe=fundamentals.roe,
                pe=fundamentals.pe,
                analyst=consensus,
                next_earnings=fundamentals.next_earnings,
                as_of=quote.as_of,
                sector_return=sector_mean.get(quote.sector, 0),
            )
        )
    return rows


def search_ideas(
    book,
    *,
    amount: Decimal,
    style: str,
    risk: str,
    filters: IdeaFilters,
    weights: dict[str, float],
) -> dict[str, object]:
    rows = rank(build_inputs(book), filters, weights, limit=5)
    ideas = [_idea(book, row, amount, style, risk, weights) for row in rows]
    return {
        "dataMode": getattr(book, "data_mode", "mock"),
        "count": len(ideas),
        "requested": 5,
        "note": (
            "Exactly five names passed the filters."
            if len(ideas) == 5
            else f"Only {len(ideas)} names passed the filters. No extra names were added."
        ),
        "disclaimer": (
            "These rankings are computed from the connected data and the configured weights. "
            "They are not a recommendation to buy, and they do not promise a profit."
        ),
        "ideas": ideas,
    }


def _idea(book, row: dict, amount: Decimal, style: str, risk: str, weights: dict[str, float]) -> dict:
    item: ScoreInput = row["input"]
    parts: dict[str, float] = row["parts"]
    bull, bear = reasons(parts)
    atr_mult, reward_1, reward_2 = STYLE_ATR.get(style, STYLE_ATR["swing"])
    risk_percent = RISK_PERCENT.get(risk, Decimal("1"))
    price = Decimal(str(round(item.price, 2)))
    plan = None
    stop = None
    target_1 = None
    target_2 = None
    if item.atr and item.atr > 0:
        stop_price = price - atr_mult * Decimal(str(item.atr))
        stop_price = stop_price.quantize(Decimal("0.01"))
        if Decimal("0") < stop_price < price:
            risk_share = price - stop_price
            target_1 = (price + reward_1 * risk_share).quantize(Decimal("0.01"))
            target_2 = (price + reward_2 * risk_share).quantize(Decimal("0.01"))
            stop = stop_price
            plan = plan_position(
                account=amount,
                risk_percent=risk_percent,
                entry=price,
                stop=stop_price,
                target=target_1,
            )
    bundle = bundle_for(item.ticker, book)
    catalyst = "No earnings date is present in the connected filings."
    if item.next_earnings and (item.next_earnings - item.as_of).days <= 45:
        catalyst = f"Earnings date {item.next_earnings.isoformat()} is within 45 days of the as-of date."
    return {
        "ticker": item.ticker,
        "company": item.company,
        "price": str(price),
        "score": row["score"],
        "confidence": _confidence(row["score"]),
        "parts": parts,
        "weights": weights,
        "compositeCheck": composite(parts, weights),
        "entryLow": str((price * Decimal("0.995")).quantize(Decimal("0.01"))),
        "entryHigh": str((price * Decimal("1.005")).quantize(Decimal("0.01"))),
        "stop": None if stop is None else str(stop),
        "target1": None if target_1 is None else str(target_1),
        "target2": None if target_2 is None else str(target_2),
        "riskReward": None if plan is None or plan.risk_reward is None else str(plan.risk_reward),
        "suggestedShares": None if plan is None else str(plan.shares),
        "suggestedAllocation": None if plan is None else str(plan.position_value),
        "bull": bull,
        "bear": bear,
        "catalyst": catalyst,
        "risks": _risks(item),
        "evidence": bundle.model_dump(mode="json", by_alias=True),
        "style": style,
        "asOf": item.as_of.isoformat(),
    }


def _confidence(score: float) -> str:
    if score >= 70:
        return "Higher"
    if score >= 55:
        return "Moderate"
    return "Lower"


def _risks(item: ScoreInput) -> list[str]:
    found = []
    if item.annualized_vol and item.annualized_vol > 0.45:
        found.append(f"Recent annualized volatility is {item.annualized_vol:.0%}.")
    if item.pe and item.pe > 45:
        found.append(f"Price over reference EPS is {item.pe:.1f}.")
    if item.rsi and item.rsi > 75:
        found.append(f"RSI is {item.rsi:.1f}, which is an extended reading on this series.")
    if not found:
        found.append("No extra risk flag fired beyond the component scores.")
    return found


def _volatility(bars) -> float | None:
    if len(bars) < 21:
        return None
    returns = []
    window = bars[-61:]
    for previous, current in zip(window, window[1:], strict=False):
        if previous.close <= 0:
            continue
        returns.append(float(current.close / previous.close - 1))
    if len(returns) < 10:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(252)


def parse_day(value: date | None) -> date | None:
    return value
