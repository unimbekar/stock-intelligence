from __future__ import annotations

import random
from datetime import timedelta
from typing import Protocol

from meridian_market.catalog import Catalog, get_catalog

from meridian_research.models import AnalystConsensus, EvidenceBundle, EvidenceItem


class NewsProvider(Protocol):
    def get_news(self, ticker: str) -> list[EvidenceItem]: ...


class ResearchProvider(Protocol):
    def get_research(self, ticker: str) -> list[EvidenceItem]: ...


class AnalystProvider(Protocol):
    def get_analyst_ratings(self, ticker: str) -> AnalystConsensus: ...


def _consensus(catalog: Catalog, ticker: str) -> AnalystConsensus:
    quote = catalog.quote(ticker)
    rng = random.Random(ticker)
    buy = 8 + rng.randint(0, 14)
    hold = 3 + rng.randint(0, 8)
    sell = rng.randint(0, 4)
    upside = (rng.random() - 0.25) * 0.28
    average = float(quote.price) * (1 + upside)
    return AnalystConsensus(
        ticker=ticker,
        consensus=_label(buy, hold, sell),
        buy=buy,
        hold=hold,
        sell=sell,
        average_target=round(average, 2),
        high_target=round(average * 1.18, 2),
        low_target=round(average * 0.78, 2),
        upside_percent=round(upside * 100, 1),
    )


def _label(buy: int, hold: int, sell: int) -> str:
    score = buy - sell
    if score >= 12:
        return "Buy"
    if score >= 6:
        return "Moderate Buy"
    if score <= 0:
        return "Hold"
    return "Hold"


class MockNewsProvider:
    def __init__(self, catalog: Catalog | None = None) -> None:
        self.catalog = catalog or get_catalog()

    def get_news(self, ticker: str) -> list[EvidenceItem]:
        symbol = ticker.upper()
        quote = self.catalog.quote(symbol)
        as_of = self.catalog.as_of
        direction = "rose" if quote.change > 0 else "fell" if quote.change < 0 else "was unchanged"
        session_name = "last regular session" if quote.data_mode == "live" else "demo session"
        return [
            EvidenceItem(
                id=f"{symbol}-news-session",
                ticker=symbol,
                source="Reuters",
                source_type="news",
                title=f"{symbol} {direction} {abs(quote.change_percent)}% in the {session_name}",
                published_on=as_of,
                author=None,
                summary=(
                    f"Session recap only. {symbol} closed at {quote.price} "
                    f"({quote.change_percent}% versus the prior close) on "
                    f"{quote.volume:,} shares. This sentence uses the connected series and "
                    f"was not retrieved from Reuters."
                ),
                url=None,
            ),
            EvidenceItem(
                id=f"{symbol}-news-sector",
                ticker=symbol,
                source="MarketWatch",
                source_type="news",
                title=f"{quote.sector} tape check for {symbol}",
                published_on=as_of - timedelta(days=1),
                summary=(
                    f"{symbol} is classified in {quote.sector} / {quote.industry} "
                    f"inside the demo universe. No external article was fetched."
                ),
                url=None,
            ),
        ]


class MockResearchProvider:
    def __init__(self, catalog: Catalog | None = None) -> None:
        self.catalog = catalog or get_catalog()

    def get_research(self, ticker: str) -> list[EvidenceItem]:
        symbol = ticker.upper()
        quote = self.catalog.quote(symbol)
        facts = self.catalog.fundamentals(symbol)
        technicals = self.catalog.technicals(symbol)
        consensus = _consensus(self.catalog, symbol)
        fair = None
        if facts.eps and facts.forward_pe:
            fair = round(float(facts.eps) * facts.forward_pe, 2)
        as_of = self.catalog.as_of
        filed = facts.source == "sec-edgar"
        growth_origin = "the SEC annual filing" if filed else "the demo file"
        filing_summary = (
            "Annual revenue, EPS, margins, and cash flow on the fundamentals panel come from "
            "SEC EDGAR company facts. This card is not the filing text, and it does not include "
            "risk factors or exhibits."
            if filed
            else (
                "No EDGAR document was retrieved. Connect a licensed or official filing "
                "adapter before treating any filing date, risk factor, or exhibit as real."
            )
        )
        items = [
            EvidenceItem(
                id=f"{symbol}-tipranks",
                ticker=symbol,
                source="TipRanks",
                source_type="analyst_opinion",
                title=f"Demo consensus for {symbol}",
                published_on=as_of,
                rating=consensus.consensus,
                price_target=consensus.average_target,
                summary=(
                    f"Illustrative split of {consensus.buy} buy, {consensus.hold} hold, "
                    f"{consensus.sell} sell. Average demo target {consensus.average_target} "
                    f"({consensus.upside_percent}% versus the demo price {quote.price}). "
                    "Counts are seeded for the local dataset and are not TipRanks data."
                ),
            ),
            EvidenceItem(
                id=f"{symbol}-barrons",
                ticker=symbol,
                source="Barron's",
                source_type="research",
                title=f"What the demo series shows for {symbol}",
                published_on=as_of - timedelta(days=3),
                author="Meridian demo desk",
                summary=(
                    f"Price {quote.price} versus SMA20 {technicals.sma20}, "
                    f"SMA50 {technicals.sma50}, SMA200 {technicals.sma200}. "
                    f"RSI {technicals.rsi}. Relative volume {technicals.relative_volume}. "
                    "Written from those figures. Not a Barron's article."
                ),
            ),
            EvidenceItem(
                id=f"{symbol}-seeking-alpha",
                ticker=symbol,
                source="Seeking Alpha",
                source_type="research",
                title=f"Demo factor snapshot for {symbol}",
                published_on=as_of - timedelta(days=6),
                rating=_quant_label(technicals.rsi, facts.revenue_growth),
                summary=(
                    f"Revenue growth in {growth_origin} is {facts.revenue_growth:.0%}. "
                    f"Operating margin is {facts.operating_margin:.0%}. "
                    f"RSI is {technicals.rsi}. The label above is a local rule, "
                    "not a Seeking Alpha quant rating."
                ),
            ),
            EvidenceItem(
                id=f"{symbol}-morningstar",
                ticker=symbol,
                source="Morningstar",
                source_type="research",
                title=f"Demo fair-value sketch for {symbol}",
                published_on=as_of - timedelta(days=12),
                price_target=fair,
                rating="Sketch" if fair else "Unavailable",
                summary=(
                    (
                        f"Sketch = demo EPS {facts.eps} × forward P/E {facts.forward_pe} "
                        f"= {fair}. This is arithmetic on the local file, not a Morningstar fair value."
                    )
                    if fair
                    else "Forward P/E is not in the connected fundamentals, so no sketch was produced."
                ),
            ),
            EvidenceItem(
                id=f"{symbol}-sec",
                ticker=symbol,
                source="SEC / Company",
                source_type="filing",
                title=f"Filing placeholder for {symbol}",
                published_on=as_of - timedelta(days=20),
                summary=filing_summary,
            ),
        ]
        return items


class MockAnalystProvider:
    def __init__(self, catalog: Catalog | None = None) -> None:
        self.catalog = catalog or get_catalog()

    def get_analyst_ratings(self, ticker: str) -> AnalystConsensus:
        return _consensus(self.catalog, ticker.upper())


def bundle_for(ticker: str, catalog: Catalog | None = None) -> EvidenceBundle:
    book = catalog or get_catalog()
    symbol = ticker.upper()
    if getattr(book, "data_mode", "mock") == "live":
        return filed_bundle(book, symbol)
    news = MockNewsProvider(book).get_news(symbol)
    research = MockResearchProvider(book).get_research(symbol)
    consensus = MockAnalystProvider(book).get_analyst_ratings(symbol)
    return EvidenceBundle(ticker=symbol, items=[*research, *news], consensus=consensus)


def filed_bundle(book, ticker: str) -> EvidenceBundle:
    from meridian_market.sec import recent_filings

    symbol = ticker.upper()
    quote = book.quote(symbol)
    technicals = book.technicals(symbol)
    facts = book.fundamentals(symbol)
    filed = facts.source == "sec-edgar"
    items = [
        EvidenceItem(
            id=f"{symbol}-session",
            ticker=symbol,
            source="Nasdaq",
            source_type="news",
            title=f"{symbol} closed at {quote.price} on {quote.as_of.isoformat()}",
            published_on=quote.as_of,
            summary=(
                f"{quote.name} last regular session close {quote.price}, "
                f"change {quote.change} ({quote.change_percent}%), volume {quote.volume:,}. "
                f"RSI {technicals.rsi}. SMA20 {technicals.sma20}. SMA50 {technicals.sma50}. "
                "Taken from the Nasdaq historical table. Not a live quote and not a news article."
            ),
            data_mode="live",
            synthetic=False,
            disclosure="Computed from the Nasdaq end-of-day table for this symbol.",
        )
    ]
    if filed:
        items.append(
            EvidenceItem(
                id=f"{symbol}-facts",
                ticker=symbol,
                source="SEC EDGAR",
                source_type="filing",
                title=f"Annual company facts for {symbol}",
                published_on=quote.as_of,
                summary=(
                    f"Filed revenue {facts.revenue:,}. Revenue growth {facts.revenue_growth:.1%}. "
                    f"Diluted EPS {facts.eps}. EPS growth {facts.eps_growth:.1%}. "
                    f"Operating margin {facts.operating_margin:.1%}. "
                    f"Free cash flow {facts.free_cash_flow:,}. "
                    f"P/E {facts.pe if facts.pe is not None else 'unavailable'}. "
                    "Forward P/E, PEG, and the next earnings date are not in this filing extract."
                ),
                data_mode="live",
                synthetic=False,
                disclosure="Annual figures from SEC EDGAR company facts. This card is not the filing document.",
            )
        )
    else:
        items.append(
            EvidenceItem(
                id=f"{symbol}-facts-missing",
                ticker=symbol,
                source="SEC EDGAR",
                source_type="filing",
                title=f"No annual company facts for {symbol}",
                published_on=quote.as_of,
                summary=(
                    "SEC company facts did not include a usable annual revenue and diluted EPS series "
                    "for this symbol. No substitute figures were filled in."
                ),
                data_mode="live",
                synthetic=False,
                disclosure="Checked against SEC EDGAR company facts.",
            )
        )
    for filing in recent_filings(symbol):
        items.append(
            EvidenceItem(
                id=f"{symbol}-{filing.form}-{filing.filed_on.isoformat()}-{filing.url[-24:]}",
                ticker=symbol,
                source="SEC EDGAR",
                source_type="filing",
                title=f"{filing.form} filed {filing.filed_on.isoformat()}",
                published_on=filing.filed_on,
                summary=filing.description,
                url=filing.url,
                data_mode="live",
                synthetic=False,
                disclosure="Link to the filing on sec.gov. The document text is not copied into Meridian.",
            )
        )
    consensus = AnalystConsensus(
        ticker=symbol,
        consensus="Unavailable",
        buy=0,
        hold=0,
        sell=0,
        average_target=0,
        high_target=0,
        low_target=0,
        upside_percent=0,
        data_mode="live",
        disclosure=(
            "No analyst-rating feed is connected. Buy, hold, sell, and price targets are not estimated."
        ),
    )
    return EvidenceBundle(ticker=symbol, items=items, consensus=consensus, data_mode="live")


def _quant_label(rsi_value: float | None, revenue_growth: float) -> str:
    if rsi_value is None:
        return "Insufficient history"
    if rsi_value >= 55 and revenue_growth >= 0.1:
        return "Constructive"
    if rsi_value <= 40:
        return "Cooling"
    return "Mixed"
