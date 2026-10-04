"""Transparent long-only ranking. Every input is a number the caller already has."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ScoreInput:
    ticker: str
    company: str
    price: float
    market_cap: int
    volume: int
    sector: str
    categories: tuple[str, ...]
    rsi: float | None
    sma20: float | None
    sma50: float | None
    sma200: float | None
    relative_volume: float | None
    atr: float | None
    annualized_vol: float | None
    revenue_growth: float | None
    eps_growth: float | None
    operating_margin: float | None
    roe: float | None
    pe: float | None
    analyst: str | None
    next_earnings: date | None
    as_of: date
    sector_return: float


@dataclass(frozen=True)
class IdeaFilters:
    categories: tuple[str, ...] = ()
    min_market_cap: int | None = None
    max_market_cap: int | None = None
    min_volume: int | None = None
    max_volatility: float | None = None
    min_price: float | None = None
    max_price: float | None = None
    analyst: str | None = None
    exclude: tuple[str, ...] = ()


def component_scores(item: ScoreInput) -> dict[str, float]:
    technical = 0.0
    if item.sma20 and item.price > item.sma20:
        technical += 30
    if item.sma50 and item.price > item.sma50:
        technical += 25
    if item.sma200 and item.price > item.sma200:
        technical += 25
    if item.rsi is not None and 45 <= item.rsi <= 70:
        technical += 20
    elif item.rsi is not None and item.rsi > 70:
        technical += 8
    else:
        technical += 10
    if item.relative_volume and item.relative_volume >= 1.2:
        technical = min(100, technical + 8)

    fundamental = 40.0
    if item.revenue_growth is not None:
        fundamental += max(-15, min(25, item.revenue_growth * 40))
    if item.operating_margin is not None:
        fundamental += max(-10, min(20, item.operating_margin * 40))
    if item.roe is not None:
        fundamental += max(-10, min(15, item.roe * 20))

    analyst_map = {"Buy": 82, "Moderate Buy": 68, "Hold": 48, "Sell": 22}
    analyst = analyst_map.get(item.analyst or "", 50)

    earnings = 50.0
    if item.eps_growth is not None:
        earnings += max(-20, min(30, item.eps_growth * 40))
    if item.revenue_growth is not None and item.revenue_growth > 0.15:
        earnings += 10
    earnings = max(0, min(100, earnings))

    if item.pe is None or item.pe <= 0:
        valuation = 50.0
    elif item.pe < 18:
        valuation = 84.0
    elif item.pe < 28:
        valuation = 68.0
    elif item.pe < 45:
        valuation = 48.0
    else:
        valuation = 28.0

    sector = max(0.0, min(100.0, 50 + item.sector_return * 400))
    vol = item.annualized_vol if item.annualized_vol is not None else 0.35
    risk = max(0.0, min(100.0, 100 - vol * 120))
    return {
        "technical_momentum": round(max(0, min(100, technical)), 1),
        "fundamental_strength": round(max(0, min(100, fundamental)), 1),
        "analyst_sentiment": analyst,
        "earnings_momentum": round(earnings, 1),
        "valuation": valuation,
        "sector_momentum": round(sector, 1),
        "risk_volatility": round(risk, 1),
    }


def composite(parts: dict[str, float], weights: dict[str, float]) -> float:
    return round(sum(parts[name] * weights[name] for name in weights), 1)


def passes(item: ScoreInput, filters: IdeaFilters) -> bool:
    if item.ticker in {ticker.upper() for ticker in filters.exclude}:
        return False
    if filters.categories and not set(filters.categories).intersection(item.categories):
        return False
    if filters.min_market_cap is not None and item.market_cap < filters.min_market_cap:
        return False
    if filters.max_market_cap is not None and item.market_cap > filters.max_market_cap:
        return False
    if filters.min_volume is not None and item.volume < filters.min_volume:
        return False
    if filters.max_volatility is not None and item.annualized_vol is not None:
        if item.annualized_vol > filters.max_volatility:
            return False
    if filters.min_price is not None and item.price < filters.min_price:
        return False
    if filters.max_price is not None and item.price > filters.max_price:
        return False
    if filters.analyst and filters.analyst != "Any":
        allowed = {filters.analyst}
        if filters.analyst == "Buy":
            allowed.add("Moderate Buy")
        if item.analyst not in allowed:
            return False
    return True


def rank(items: list[ScoreInput], filters: IdeaFilters, weights: dict[str, float], limit: int = 5) -> list[dict]:
    ranked: list[dict] = []
    for item in items:
        if not passes(item, filters):
            continue
        parts = component_scores(item)
        score = composite(parts, weights)
        ranked.append({"input": item, "parts": parts, "score": score})
    ranked.sort(key=lambda row: (-row["score"], row["input"].ticker))
    return ranked[:limit]


def reasons(parts: dict[str, float]) -> tuple[list[str], list[str]]:
    labels = {
        "technical_momentum": "Technical momentum",
        "fundamental_strength": "Fundamental strength",
        "analyst_sentiment": "Analyst sentiment",
        "earnings_momentum": "Earnings momentum",
        "valuation": "Valuation",
        "sector_momentum": "Sector momentum",
        "risk_volatility": "Risk and volatility",
    }
    bull = [f"{labels[name]} scored {parts[name]:.0f}" for name, _score in parts.items() if parts[name] >= 65]
    bear = [f"{labels[name]} scored {parts[name]:.0f}" for name in parts if parts[name] <= 42]
    if not bull:
        bull = ["No component is firmly supportive on the current inputs."]
    if not bear:
        bear = ["No component is firmly weak on the current inputs."]
    return bull, bear
