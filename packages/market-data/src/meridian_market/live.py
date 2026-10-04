"""End-of-day prices from Nasdaq's public historical quote table.

This is the last regular session in that table, not a live tape and not a
licensed research feed. Additional symbols are loaded from the same table
when someone looks them up. If the download fails, the caller should keep
the demo book.
"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from urllib.error import URLError
from urllib.request import Request, urlopen

from meridian_market.catalog import technicals_from_bars
from meridian_market.models import Bar, Fundamentals, IndexQuote, Instrument, Quote
from meridian_market.universe import UNIVERSE

USER_AGENT = "Mozilla/5.0"
NASDAQ = "https://api.nasdaq.com/api/quote"
# Nasdaq publishes the index level for NDX. The other benchmarks are the
# matching ETFs, labeled as proxies so they are not shown as the index itself.
INDEX_SERIES = (
    ("NDX", "index", "NASDAQ 100"),
    ("SPY", "etf", "S&P 500 proxy (SPY)"),
    ("DIA", "etf", "Dow proxy (DIA)"),
    ("IWM", "etf", "Russell 2000 proxy (IWM)"),
)


class LiveBook:
    def __init__(self, equity: dict[str, list[Bar]], indexes: dict[str, tuple[str, list[Bar]]]) -> None:
        self._equity = equity
        self._indexes = indexes
        self.instruments = {item.ticker: item for item in UNIVERSE if item.ticker in equity}
        dates = [bars[-1].session for bars in equity.values() if bars]
        self.as_of = max(dates) if dates else date.today()
        self.data_mode = "live"
        self.source = "nasdaq"
        self._core = set(equity)
        self._missing: set[str] = set()
        self._lock = threading.Lock()
        self.warning = (
            "Prices are the last regular session in Nasdaq's public historical table. Not a live quote. "
            "Annual fundamentals and filing links come from SEC EDGAR when that company files. "
            "P/E uses that session's close and the filed diluted EPS. "
            "No analyst-rating feed is connected, so buy, hold, sell, and price targets are not estimated."
        )

    @classmethod
    def load(cls) -> LiveBook:
        jobs: list[tuple[str, str, str]] = [("equity", item.ticker, "stocks") for item in UNIVERSE]
        jobs.extend(("index", symbol, asset) for symbol, asset, _name in INDEX_SERIES)
        downloaded: dict[tuple[str, str], list[Bar]] = {}
        with ThreadPoolExecutor(max_workers=4) as pool:
            future_map = {pool.submit(_download, symbol, asset): (kind, symbol) for kind, symbol, asset in jobs}
            for future in as_completed(future_map):
                kind, symbol = future_map[future]
                try:
                    bars = future.result()
                except (URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError):
                    bars = []
                downloaded[(kind, symbol)] = bars
        equity = {item.ticker: downloaded[("equity", item.ticker)] for item in UNIVERSE}
        equity = {ticker: bars for ticker, bars in equity.items() if len(bars) >= 30}
        indexes = {
            symbol: (name, downloaded[("index", symbol)])
            for symbol, _asset, name in INDEX_SERIES
            if len(downloaded.get(("index", symbol), [])) >= 2
        }
        if len(equity) < 10:
            raise RuntimeError("Nasdaq returned fewer than 10 equity series")
        return cls(equity, indexes)

    def require(self, ticker: str) -> None:
        self.admit(ticker)

    def admit(self, ticker: str) -> None:
        symbol = ticker.strip().upper()
        if symbol in self._equity and len(self._equity[symbol]) >= 2:
            return
        if not symbol or not symbol.replace(".", "").replace("-", "").isalnum():
            raise KeyError(ticker)
        with self._lock:
            if symbol in self._equity and len(self._equity[symbol]) >= 2:
                return
            if symbol in self._missing:
                raise KeyError(symbol)
            bars = _download_any(symbol)
            if len(bars) < 2:
                self._missing.add(symbol)
                raise KeyError(symbol)
            self._equity[symbol] = bars
            if symbol not in self.instruments:
                self.instruments[symbol] = _instrument_for(symbol, bars)

    def bars(self, ticker: str) -> list[Bar]:
        self.require(ticker)
        return self._equity[ticker.upper()]

    def quote(self, ticker: str) -> Quote:
        self.require(ticker)
        instrument = self.instruments[ticker.upper()]
        bars = self._equity[instrument.ticker]
        last = bars[-1]
        previous = bars[-2].close
        change = last.close - previous
        change_percent = (change / previous) * Decimal("100")
        market_cap = _market_cap(instrument.ticker, last.close, instrument.market_cap, instrument.anchor_price)
        return Quote(
            ticker=instrument.ticker,
            name=instrument.name,
            price=last.close,
            change=change.quantize(Decimal("0.01")),
            change_percent=change_percent.quantize(Decimal("0.01")),
            volume=last.volume,
            market_cap=market_cap,
            sector=instrument.sector,
            industry=instrument.industry,
            categories=instrument.categories,
            as_of=last.session,
            data_mode="live",
            source="nasdaq",
        )

    def quotes(self) -> list[Quote]:
        return [self.quote(ticker) for ticker in self._core if ticker in self._equity]

    def fundamentals(self, ticker: str) -> Fundamentals:
        self.require(ticker)
        from meridian_market.sec import ensure_fundamental

        price = self.quote(ticker).price
        filed = ensure_fundamental(ticker, price)
        if filed is not None:
            return filed
        return Fundamentals(
            ticker=ticker.upper(),
            revenue=0,
            revenue_growth=0,
            eps=Decimal("0"),
            eps_growth=0,
            gross_margin=0,
            operating_margin=0,
            free_cash_flow=0,
            pe=None,
            forward_pe=None,
            peg=None,
            price_to_sales=None,
            debt_to_equity=None,
            roe=None,
            roic=None,
            next_earnings=None,
            data_mode="live",
            source="unavailable",
        )

    def technicals(self, ticker: str):
        bars = self.bars(ticker)
        return technicals_from_bars(
            ticker,
            bars[-1].session,
            bars,
            "Indicators use Nasdaq end-of-day prices. Support and resistance are the 20-session low and high.",
            data_mode="live",
        )

    def index_quotes(self) -> list[IndexQuote]:
        rows: list[IndexQuote] = []
        for symbol, (name, bars) in self._indexes.items():
            change = bars[-1].close - bars[-2].close
            change_percent = (change / bars[-2].close) * Decimal("100")
            rows.append(
                IndexQuote(
                    symbol=symbol,
                    name=name,
                    value=bars[-1].close,
                    change=change.quantize(Decimal("0.01")),
                    change_percent=change_percent.quantize(Decimal("0.01")),
                    as_of=bars[-1].session,
                    data_mode="live",
                )
            )
        return rows

    def sentiment(self):
        from meridian_market.models import MarketSentiment, SentimentFactor

        quotes = self.quotes()
        advancers = sum(1 for quote in quotes if quote.change > 0)
        breadth = 100 * advancers / len(quotes) if quotes else 50
        indexes = {item.symbol: item for item in self.index_quotes()}
        benchmark = indexes.get("SPY") or indexes.get("NDX")
        change = float(benchmark.change_percent) if benchmark else 0
        momentum = max(0.0, min(100.0, 50 + change * 25))
        volatility = 50.0
        sector = self._sector_score()
        factors = [
            SentimentFactor(name="Technical Momentum", score=round(momentum, 1), label=_band(momentum)),
            SentimentFactor(name="Market Breadth", score=round(breadth, 1), label=_band(breadth)),
            SentimentFactor(name="Volatility", score=round(volatility, 1), label=_band(volatility)),
            SentimentFactor(name="Sector Momentum", score=round(sector, 1), label=_band(sector)),
            SentimentFactor(name="Earnings Environment", score=50, label="Mixed"),
            SentimentFactor(name="Analyst Sentiment", score=50, label="Mixed"),
        ]
        blended = sum(factor.score for factor in factors) / len(factors)
        note = (
            "Breadth and sector returns use the Nasdaq session closes. "
            "Index momentum uses the SPY or NASDAQ 100 change when that series loaded. "
            "VIX was not in this table, so the volatility factor stays neutral. "
            "Earnings environment and analyst sentiment stay neutral because no licensed feed is connected."
        )
        return MarketSentiment(
            stance=_stance(blended),
            score=round(blended, 1),
            factors=factors,
            as_of=self.as_of,
            data_mode="live",
            note=note,
        )

    def _sector_score(self) -> float:
        grouped: dict[str, list[float]] = {}
        for ticker, instrument in self.instruments.items():
            if ticker not in self._core:
                continue
            bars = self._equity[ticker]
            if len(bars) < 21:
                continue
            change = float((bars[-1].close - bars[-21].close) / bars[-21].close)
            grouped.setdefault(instrument.sector, []).append(change)
        if not grouped:
            return 50.0
        means = [sum(values) / len(values) for values in grouped.values()]
        average = sum(means) / len(means)
        return max(0.0, min(100.0, 50 + average * 400))

    def generated_at(self) -> datetime:
        return datetime.combine(self.as_of, datetime.min.time())


def _market_cap(ticker: str, price: Decimal, reference_cap: int, anchor: Decimal) -> int:
    from meridian_market.sec import ensure_fundamental

    filed = ensure_fundamental(ticker, price)
    shares = getattr(filed, "shares_outstanding", None) if filed is not None else None
    if shares:
        return int(price * Decimal(shares))
    if anchor:
        return int(reference_cap * float(price / anchor))
    return reference_cap


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


def parse_nasdaq_rows(rows: list[dict]) -> list[Bar]:
    bars: list[Bar] = []
    for record in rows:
        try:
            session = _us_date(str(record["date"]))
            close = _money(str(record["close"]))
            open_ = _money(str(record.get("open") or record["close"]))
            high = _money(str(record.get("high") or record["close"]))
            low = _money(str(record.get("low") or record["close"]))
            volume = int(str(record.get("volume") or "0").replace(",", ""))
        except (KeyError, ValueError, ArithmeticError):
            continue
        if min(open_, high, low, close) <= 0:
            continue
        bars.append(
            Bar(
                session=session,
                open=open_,
                high=max(high, open_, close),
                low=min(low, open_, close),
                close=close,
                volume=volume,
            )
        )
    bars.sort(key=lambda bar: bar.session)
    return bars[-320:]


def _instrument_for(symbol: str, bars: list[Bar]) -> Instrument:
    from meridian_market.symbols import get_directory

    listing = get_directory().lookup(symbol)
    name = listing.name if listing is not None else symbol
    last = bars[-1].close
    volume = int(sum(bar.volume for bar in bars[-20:]) / min(20, len(bars)))
    return Instrument(
        ticker=symbol,
        name=name,
        sector="Unclassified",
        industry="",
        categories=[],
        anchor_price=last,
        start_price=bars[0].close,
        market_cap=0,
        beta=1.0,
        avg_volume=volume,
        annualized_vol=0.3,
        seed=0,
        description="Listed company resolved from the SEC ticker file and the Nasdaq session table.",
    )


def _download_any(symbol: str) -> list[Bar]:
    for asset in ("stocks", "etf"):
        try:
            return _download(symbol, asset)
        except (URLError, TimeoutError, ValueError, OSError, json.JSONDecodeError):
            continue
    return []


def _download(symbol: str, asset_class: str) -> list[Bar]:
    url = (
        f"{NASDAQ}/{symbol}/historical?assetclass={asset_class}"
        "&fromdate=2025-01-01&todate=2026-10-04&limit=400"
    )
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)
    rows = ((payload.get("data") or {}).get("tradesTable") or {}).get("rows") or []
    bars = parse_nasdaq_rows(rows)
    if len(bars) < 2:
        raise ValueError(f"No Nasdaq history for {symbol}")
    return bars


def _us_date(text: str) -> date:
    month, day, year = text.split("/")
    return date(int(year), int(month), int(day))


def _money(text: str) -> Decimal:
    return Decimal(text.replace("$", "").replace(",", "").strip()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
