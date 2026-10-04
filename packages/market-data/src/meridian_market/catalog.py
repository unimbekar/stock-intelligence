from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache

from meridian_market.indicators import (
    atr,
    ema,
    macd,
    relative_volume,
    round_or_none,
    rsi,
    sma,
)
from meridian_market.models import (
    Bar,
    Fundamentals,
    IndexQuote,
    Instrument,
    MarketSentiment,
    Quote,
    SentimentFactor,
    TechnicalSnapshot,
)
from meridian_market.series import build_bars, last_weekday
from meridian_market.universe import FUNDAMENTALS, INDEXES, UNIVERSE


class Catalog:
    """In-memory demo book. Built once per process from a fixed seed."""

    def __init__(self, as_of: date | None = None) -> None:
        self.as_of = last_weekday(as_of or date.today())
        self.instruments = {item.ticker: item for item in UNIVERSE}
        self._equity: dict[str, list[Bar]] = {}
        self._index: dict[str, list[Bar]] = {}
        for item in UNIVERSE:
            self._equity[item.ticker] = build_bars(
                anchor=item.anchor_price,
                start=item.start_price,
                annualized_vol=item.annualized_vol,
                seed=item.seed,
                end=self.as_of,
                base_volume=item.avg_volume,
            )
        for item in INDEXES:
            self._index[item["symbol"]] = build_bars(
                anchor=item["anchor"],
                start=item["start"],
                annualized_vol=item["vol"],
                seed=item["seed"],
                end=self.as_of,
                base_volume=1,
            )

    def list_instruments(self) -> list[Instrument]:
        return list(self.instruments.values())

    def require(self, ticker: str) -> Instrument:
        key = ticker.upper()
        try:
            return self.instruments[key]
        except KeyError as exc:
            raise KeyError(f"Unknown ticker {ticker}") from exc

    def bars(self, ticker: str) -> list[Bar]:
        self.require(ticker)
        return self._equity[ticker.upper()]

    def quote(self, ticker: str) -> Quote:
        instrument = self.require(ticker)
        bars = self.bars(instrument.ticker)
        last = bars[-1]
        previous = bars[-2].close
        change = last.close - previous
        change_percent = (change / previous) * Decimal("100")
        return Quote(
            ticker=instrument.ticker,
            name=instrument.name,
            price=last.close,
            change=change.quantize(Decimal("0.01")),
            change_percent=change_percent.quantize(Decimal("0.01")),
            volume=last.volume,
            market_cap=instrument.market_cap,
            sector=instrument.sector,
            industry=instrument.industry,
            categories=instrument.categories,
            as_of=self.as_of,
        )

    def quotes(self) -> list[Quote]:
        return [self.quote(item.ticker) for item in UNIVERSE]

    def fundamentals(self, ticker: str) -> Fundamentals:
        self.require(ticker)
        return FUNDAMENTALS[ticker.upper()]

    def technicals(self, ticker: str) -> TechnicalSnapshot:
        return technicals_from_bars(
            ticker,
            self.as_of,
            self.bars(ticker),
            "Indicators use the demo price series. Support and resistance are the 20-session low and high.",
        )

    def index_quotes(self) -> list[IndexQuote]:
        names = {item["symbol"]: item["name"] for item in INDEXES}
        quotes: list[IndexQuote] = []
        for symbol, bars in self._index.items():
            change = bars[-1].close - bars[-2].close
            change_percent = (change / bars[-2].close) * Decimal("100")
            quotes.append(
                IndexQuote(
                    symbol=symbol,
                    name=names[symbol],
                    value=bars[-1].close,
                    change=change.quantize(Decimal("0.01")),
                    change_percent=change_percent.quantize(Decimal("0.01")),
                    as_of=self.as_of,
                )
            )
        return quotes

    def sentiment(self) -> MarketSentiment:
        indexes = {item.symbol: item for item in self.index_quotes()}
        spx = float(indexes["SPX"].change_percent)
        breadth = self._breadth()
        vix = float(indexes["VIX"].value)
        volatility_score = max(0.0, min(100.0, (28 - vix) / 20 * 100))
        momentum_score = max(0.0, min(100.0, 50 + spx * 25))
        sector_score = self._sector_momentum_score()
        earnings_score = 58.0
        analyst_score = 61.0
        factors = [
            SentimentFactor(name="Technical Momentum", score=round(momentum_score, 1), label=_band(momentum_score)),
            SentimentFactor(name="Market Breadth", score=round(breadth, 1), label=_band(breadth)),
            SentimentFactor(name="Volatility", score=round(volatility_score, 1), label=_band(volatility_score)),
            SentimentFactor(name="Sector Momentum", score=round(sector_score, 1), label=_band(sector_score)),
            SentimentFactor(name="Earnings Environment", score=earnings_score, label=_band(earnings_score)),
            SentimentFactor(name="Analyst Sentiment", score=analyst_score, label=_band(analyst_score)),
        ]
        # Earnings and analyst factors are neutral placeholders until those
        # providers feed the score. They are labeled as such via the note.
        blended = sum(factor.score for factor in factors) / len(factors)
        return MarketSentiment(
            stance=_stance(blended),
            score=round(blended, 1),
            factors=factors,
            as_of=self.as_of,
            note=(
                "Technical momentum, breadth, volatility, and sector momentum are computed "
                "from the demo series. Earnings environment and analyst sentiment are neutral "
                "placeholders until those providers are wired in."
            ),
        )

    def _breadth(self) -> float:
        advancers = 0
        for ticker in self.instruments:
            quote = self.quote(ticker)
            if quote.change > 0:
                advancers += 1
        return 100 * advancers / len(self.instruments)

    def _sector_momentum_score(self) -> float:
        by_sector: dict[str, list[float]] = {}
        for ticker, instrument in self.instruments.items():
            bars = self._equity[ticker]
            if len(bars) < 21:
                continue
            change = float((bars[-1].close - bars[-21].close) / bars[-21].close)
            by_sector.setdefault(instrument.sector, []).append(change)
        if not by_sector:
            return 50.0
        sector_means = [sum(values) / len(values) for values in by_sector.values()]
        average = sum(sector_means) / len(sector_means)
        return max(0.0, min(100.0, 50 + average * 400))

    def generated_at(self) -> datetime:
        return datetime.combine(self.as_of, datetime.min.time())


def technicals_from_bars(
    ticker: str,
    as_of: date,
    bars: list[Bar],
    note: str,
    data_mode: str = "mock",
) -> TechnicalSnapshot:
    closes = [float(bar.close) for bar in bars]
    highs = [float(bar.high) for bar in bars]
    lows = [float(bar.low) for bar in bars]
    volumes = [float(bar.volume) for bar in bars]
    macd_line, signal, histogram = macd(closes)
    window = bars[-20:]
    return TechnicalSnapshot(
        ticker=ticker.upper(),
        as_of=as_of,
        rsi=round_or_none(rsi(closes)[-1], 2),
        macd=round_or_none(macd_line[-1], 4),
        macd_signal=round_or_none(signal[-1], 4),
        macd_histogram=round_or_none(histogram[-1], 4),
        sma20=round_or_none(sma(closes, 20)[-1], 2),
        sma50=round_or_none(sma(closes, 50)[-1], 2),
        sma200=round_or_none(sma(closes, 200)[-1], 2),
        ema20=round_or_none(ema(closes, 20)[-1], 2),
        atr=round_or_none(atr(highs, lows, closes)[-1], 2),
        volume=bars[-1].volume,
        relative_volume=round_or_none(relative_volume(volumes)[-1], 2),
        support=round(min(float(bar.low) for bar in window), 2),
        resistance=round(max(float(bar.high) for bar in window), 2),
        data_mode=data_mode,
        method_note=note,
    )


def _band(score: float) -> str:
    if score >= 60:
        return "Supportive"
    if score <= 40:
        return "Cautious"
    return "Mixed"


def _stance(score: float) -> str:
    if score >= 60:
        return "Bullish"
    if score <= 40:
        return "Bearish"
    return "Neutral"


@lru_cache(maxsize=1)
def get_catalog() -> Catalog:
    return Catalog()
