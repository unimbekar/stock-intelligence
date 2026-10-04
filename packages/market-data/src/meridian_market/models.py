from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


def _camel(name: str) -> str:
    head, *tail = name.split("_")
    return head + "".join(part.capitalize() for part in tail)


class Model(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True)


class Instrument(Model):
    ticker: str
    name: str
    sector: str
    industry: str
    categories: list[str]
    exchange: str = "NASDAQ"
    anchor_price: Decimal
    start_price: Decimal
    market_cap: int
    beta: float
    avg_volume: int
    annualized_vol: float
    seed: int
    description: str


class Bar(Model):
    session: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class Quote(Model):
    ticker: str
    name: str
    price: Decimal
    change: Decimal
    change_percent: Decimal
    volume: int
    market_cap: int
    sector: str
    industry: str
    categories: list[str]
    as_of: date
    data_mode: str = "mock"
    source: str = "mock"


class Fundamentals(Model):
    ticker: str
    revenue: int
    revenue_growth: float
    eps: Decimal
    eps_growth: float
    gross_margin: float
    operating_margin: float
    free_cash_flow: int
    pe: float | None
    forward_pe: float | None
    peg: float | None
    price_to_sales: float | None
    debt_to_equity: float | None
    roe: float | None
    roic: float | None
    next_earnings: date | None
    shares_outstanding: int | None = None
    data_mode: str = "mock"
    source: str = "mock"


class TechnicalSnapshot(Model):
    ticker: str
    as_of: date
    rsi: float | None
    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
    sma20: float | None
    sma50: float | None
    sma200: float | None
    ema20: float | None
    atr: float | None
    volume: int
    relative_volume: float | None
    support: float | None
    resistance: float | None
    data_mode: str = "mock"
    method_note: str = (
        "Indicators are computed from the demo price series. Support and resistance are the 20-session low and high."
    )


class IndexQuote(Model):
    symbol: str
    name: str
    value: Decimal
    change: Decimal
    change_percent: Decimal
    as_of: date
    data_mode: str = "mock"


class SentimentFactor(Model):
    name: str
    score: float = Field(ge=0, le=100)
    label: str


class MarketSentiment(Model):
    stance: str
    score: float
    factors: list[SentimentFactor]
    as_of: date
    data_mode: str = "mock"
    note: str = "Derived only from the demo index and sector series. Not a live sentiment feed."


class HistoryPage(Model):
    ticker: str
    bars: list[Bar]
    data_mode: str = "mock"
    as_of: datetime
