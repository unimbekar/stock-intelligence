from __future__ import annotations

import logging
import threading
import time

from meridian_config.settings import get_settings
from meridian_market.catalog import Catalog, get_catalog
from meridian_market.live import LiveBook
from meridian_market.models import Fundamentals
from meridian_market.sec import load_sec_fundamentals

logger = logging.getLogger("meridian.gateway")
_cache: tuple[float, object] | None = None
_fallback_reason = ""
_load_lock = threading.Lock()


class SecBook:
    """Demo prices with EDGAR fundamentals when a daily tape is unavailable."""

    def __init__(self, catalog: Catalog, facts: dict[str, Fundamentals]) -> None:
        self._catalog = catalog
        self.facts = facts
        self.instruments = catalog.instruments
        self.as_of = catalog.as_of
        self.data_mode = "mixed"
        self.source = "sec-edgar"

    def require(self, ticker: str):
        return self._catalog.require(ticker)

    def bars(self, ticker: str):
        return self._catalog.bars(ticker)

    def quote(self, ticker: str):
        return self._catalog.quote(ticker)

    def quotes(self):
        return self._catalog.quotes()

    def technicals(self, ticker: str):
        return self._catalog.technicals(ticker)

    def index_quotes(self):
        return self._catalog.index_quotes()

    def sentiment(self):
        return self._catalog.sentiment()

    def fundamentals(self, ticker: str) -> Fundamentals:
        self.require(ticker)
        filed = self.facts.get(ticker.upper())
        if filed is not None:
            return filed
        return self._catalog.fundamentals(ticker)


def active_book() -> Catalog | LiveBook | SecBook:
    global _cache, _fallback_reason
    settings = get_settings()
    if settings.data_mode != "live":
        _fallback_reason = ""
        return get_catalog()
    now = time.time()
    with _load_lock:
        if _cache and now - _cache[0] < 900:
            return _cache[1]
        return _load_live(now)


def _load_live(now: float) -> Catalog | LiveBook | SecBook:
    global _cache, _fallback_reason
    try:
        book = LiveBook.load()
        load_sec_fundamentals()
        _cache = (now, book)
        _fallback_reason = ""
        return book
    except Exception as exc:
        logger.warning("live prices unavailable: %s", exc.__class__.__name__)
        facts = load_sec_fundamentals()
        if facts:
            book = SecBook(get_catalog(), facts)
            _cache = (now, book)
            _fallback_reason = (
                "Nasdaq did not return the end-of-day table. "
                "Prices and charts stay on the labeled series. "
                f"Fundamentals for {len(facts)} companies are annual figures from SEC EDGAR company facts."
            )
            return book
        _fallback_reason = "Live prices and SEC fundamentals could not be loaded. Showing the labeled demo series."
        return get_catalog()


def data_status() -> dict[str, str]:
    book = active_book()
    mode = getattr(book, "data_mode", "mock")
    if mode == "live":
        return {
            "dataMode": "live",
            "dataModeLabel": "EOD DATA",
            "source": "Nasdaq end-of-day",
            "warning": getattr(book, "warning", ""),
        }
    if mode == "mixed":
        return {
            "dataMode": "mixed",
            "dataModeLabel": "SEC + DEMO PRICES",
            "source": "SEC EDGAR company facts; demo price series",
            "warning": _fallback_reason,
        }
    return {
        "dataMode": "mock",
        "dataModeLabel": "DEMO DATA",
        "source": "local demo series",
        "warning": _fallback_reason,
    }
