from __future__ import annotations

from typing import Protocol

from meridian_market.catalog import Catalog, get_catalog
from meridian_market.models import (
    Bar,
    Fundamentals,
    IndexQuote,
    MarketSentiment,
    Quote,
    TechnicalSnapshot,
)


class MarketDataProvider(Protocol):
    def get_quote(self, ticker: str) -> Quote: ...

    def list_quotes(self) -> list[Quote]: ...

    def get_history(self, ticker: str) -> list[Bar]: ...

    def get_indexes(self) -> list[IndexQuote]: ...

    def get_sentiment(self) -> MarketSentiment: ...


class FundamentalDataProvider(Protocol):
    def get_fundamentals(self, ticker: str) -> Fundamentals: ...


class TechnicalDataProvider(Protocol):
    def get_technicals(self, ticker: str) -> TechnicalSnapshot: ...


class MockMarketDataProvider:
    def __init__(self, catalog: Catalog | None = None) -> None:
        self.catalog = catalog or get_catalog()

    def get_quote(self, ticker: str) -> Quote:
        return self.catalog.quote(ticker)

    def list_quotes(self) -> list[Quote]:
        return self.catalog.quotes()

    def get_history(self, ticker: str) -> list[Bar]:
        return self.catalog.bars(ticker)

    def get_indexes(self) -> list[IndexQuote]:
        return self.catalog.index_quotes()

    def get_sentiment(self) -> MarketSentiment:
        return self.catalog.sentiment()


class MockFundamentalProvider:
    def __init__(self, catalog: Catalog | None = None) -> None:
        self.catalog = catalog or get_catalog()

    def get_fundamentals(self, ticker: str) -> Fundamentals:
        return self.catalog.fundamentals(ticker)


class ComputedTechnicalProvider:
    def __init__(self, catalog: Catalog | None = None) -> None:
        self.catalog = catalog or get_catalog()

    def get_technicals(self, ticker: str) -> TechnicalSnapshot:
        return self.catalog.technicals(ticker)
