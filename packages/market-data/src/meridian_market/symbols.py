"""US listing directory from the SEC company ticker file.

Search matches a ticker or a company name. It does not invent symbols.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from urllib.request import Request, urlopen

USER_AGENT = "Meridian local research desk admin@meridian.local"
TICKER_FILE = "https://www.sec.gov/files/company_tickers.json"
_WORD = re.compile(r"\b[A-Za-z]{2,5}\b")
_NAME = re.compile(r"[A-Za-z]{4,}")

# Words that look like tickers in ordinary questions.
STOP = frozenset(
    {
        "AI",
        "ALL",
        "AND",
        "ANY",
        "ARE",
        "BUT",
        "DID",
        "HAD",
        "HER",
        "HIS",
        "ITS",
        "MAY",
        "MOST",
        "NEW",
        "ONE",
        "OR",
        "OUR",
        "OUT",
        "TWO",
        "WAS",
        "ATR",
        "BUY",
        "CAN",
        "CASH",
        "CLOSE",
        "EMA",
        "EOD",
        "EPS",
        "ETF",
        "FOR",
        "FROM",
        "HAS",
        "HAVE",
        "HELP",
        "HIGH",
        "HOLD",
        "HOW",
        "IDEA",
        "IDEAS",
        "LAST",
        "LOW",
        "MACD",
        "NOT",
        "NOTE",
        "OPEN",
        "PEG",
        "PER",
        "PLEASE",
        "PRICE",
        "RSI",
        "SEC",
        "SELL",
        "SHOW",
        "SIZE",
        "SMA",
        "STOP",
        "TELL",
        "THAT",
        "THE",
        "THIS",
        "USD",
        "WHAT",
        "WHEN",
        "WHERE",
        "WHO",
        "WHY",
        "WITH",
        "YOU",
        "YOUR",
        "ABOUT",
        "ANALYZE",
        "ANALYSE",
        "COMPANY",
        "FILING",
        "FILINGS",
        "GIVE",
        "GROWTH",
        "LATEST",
        "MARGIN",
        "MARKET",
        "MARKETS",
        "PORTFOLIO",
        "QUOTE",
        "RESEARCH",
        "RETURN",
        "RETURNS",
        "REVENUE",
        "STOCK",
        "STOCKS",
        "SUMMARY",
        "SUMMARIZE",
        "TARGET",
        "TRADE",
        "WATCHLIST",
    }
)

_directory: SymbolDirectory | None = None
_lock = threading.Lock()


@dataclass(frozen=True)
class Listing:
    ticker: str
    name: str
    cik: str


class SymbolDirectory:
    def __init__(self, listings: list[Listing]) -> None:
        self._by_ticker: dict[str, Listing] = {}
        for row in listings:
            self._by_ticker.setdefault(row.ticker, row)
        self._rows = list(self._by_ticker.values())

    def lookup(self, ticker: str) -> Listing | None:
        return self._by_ticker.get(ticker.strip().upper())

    def search(self, query: str, limit: int = 8) -> list[Listing]:
        needle = " ".join(query.upper().split())
        if not needle:
            return []
        exact: list[Listing] = []
        prefix: list[Listing] = []
        name_start: list[Listing] = []
        name_has: list[Listing] = []
        for row in self._rows:
            name = row.name.upper()
            if row.ticker == needle:
                exact.append(row)
            elif row.ticker.startswith(needle):
                prefix.append(row)
            elif name.startswith(needle):
                name_start.append(row)
            elif needle in name:
                name_has.append(row)
        prefix.sort(key=lambda row: (len(row.ticker), row.ticker))
        name_start.sort(key=lambda row: row.name)
        name_has.sort(key=lambda row: row.name)
        return (exact + prefix + name_start + name_has)[:limit]


def parse_company_tickers(payload: dict) -> list[Listing]:
    rows: list[Listing] = []
    values = payload.values() if isinstance(payload, dict) else payload
    for item in values:
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker", "")).upper().strip()
        cik_raw = item.get("cik_str")
        if not ticker or cik_raw is None:
            continue
        rows.append(
            Listing(
                ticker=ticker,
                name=str(item.get("title") or ticker).strip(),
                cik=str(int(cik_raw)).zfill(10),
            )
        )
    return rows


def mentioned_symbols(question: str, known: set[str], directory: SymbolDirectory) -> list[str]:
    found: list[str] = []
    for token in _WORD.findall(question.upper()):
        if len(token) < 2 or token in STOP:
            continue
        if token in known or directory.lookup(token) is not None:
            found.append(token)
    if found:
        return list(dict.fromkeys(found))[:3]
    for word in _NAME.findall(question):
        token = word.upper()
        if token in STOP or len(token) < 4:
            continue
        for match in directory.search(word, limit=5):
            parts = re.findall(r"[A-Z0-9]+", match.name.upper())
            if any(part.startswith(token) for part in parts):
                return [match.ticker]
    return []


def get_directory() -> SymbolDirectory:
    global _directory
    if _directory is not None:
        return _directory
    with _lock:
        if _directory is not None:
            return _directory
        try:
            rows = parse_company_tickers(_download())
        except (OSError, ValueError, TimeoutError, json.JSONDecodeError):
            return SymbolDirectory([])
        if not rows:
            return SymbolDirectory([])
        _directory = SymbolDirectory(rows)
        return _directory


def _download() -> dict:
    request = Request(TICKER_FILE, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise ValueError("SEC ticker file was not an object")
    return payload
