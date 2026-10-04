"""SEC EDGAR company facts and recent filings. Official records, not a price feed."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from urllib.request import Request, urlopen

from meridian_market.models import Fundamentals

USER_AGENT = "Meridian local research desk admin@meridian.local"
CIKS = {
    "NVDA": "0001045810",
    "AMD": "0000002488",
    "MSFT": "0000789019",
    "AAPL": "0000320193",
    "AMZN": "0001018724",
    "GOOGL": "0001652044",
    "META": "0001326801",
    "TSLA": "0001318605",
    "AVGO": "0001730168",
    "PLTR": "0001321655",
    "JPM": "0000019617",
    "LLY": "0000059478",
    "NFLX": "0001065280",
    "COST": "0000909832",
    "CRWD": "0001535527",
}
REVENUE_CONCEPTS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
)
_cache: dict[str, Fundamentals] | None = None
_filing_cache: dict[str, list[Filing]] = {}


@dataclass(frozen=True)
class Filing:
    form: str
    filed_on: date
    description: str
    url: str


def annual_series(facts: dict, concepts: tuple[str, ...], unit: str) -> list[tuple[str, float]]:
    usgaap = facts.get("us-gaap", {})
    best: list[tuple[str, float]] = []
    for concept in concepts:
        rows = usgaap.get(concept, {}).get("units", {}).get(unit, [])
        deduped: dict[str, float] = {}
        for row in rows:
            if row.get("form") not in {"10-K", "10-K/A"} or row.get("fp") != "FY" or row.get("val") is None:
                continue
            deduped[str(row.get("end", ""))] = float(row["val"])
        series = sorted(deduped.items())
        if series and (not best or series[-1][0] > best[-1][0]):
            best = series
    return best


def build_fundamentals(ticker: str, facts: dict, price: Decimal | None) -> Fundamentals | None:
    revenue = annual_series(facts, REVENUE_CONCEPTS, "USD")
    eps = annual_series(
        facts,
        ("EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"),
        "USD/shares",
    )
    if len(revenue) < 1 or len(eps) < 1:
        return None
    gross = annual_series(facts, ("GrossProfit",), "USD")
    operating = annual_series(facts, ("OperatingIncomeLoss",), "USD")
    cash = annual_series(facts, ("NetCashProvidedByUsedInOperatingActivities",), "USD")
    capex = annual_series(facts, ("PaymentsToAcquirePropertyPlantAndEquipment",), "USD")
    equity = annual_series(facts, ("StockholdersEquity",), "USD")
    income = annual_series(facts, ("NetIncomeLoss",), "USD")
    debt = annual_series(facts, ("LongTermDebt", "LongTermDebtNoncurrent"), "USD")
    latest_revenue = revenue[-1][1]
    latest_eps = eps[-1][1]
    free_cash = 0
    if cash and capex:
        free_cash = int(cash[-1][1] - abs(capex[-1][1]))
    pe = None
    price_to_sales = None
    if price is not None and latest_eps:
        pe = round(float(price) / latest_eps, 2)
    return Fundamentals(
        ticker=ticker,
        revenue=int(latest_revenue),
        revenue_growth=_growth(revenue),
        eps=Decimal(str(latest_eps)),
        eps_growth=_growth(eps),
        gross_margin=_ratio(gross, latest_revenue),
        operating_margin=_ratio(operating, latest_revenue),
        free_cash_flow=free_cash,
        pe=pe,
        forward_pe=None,
        peg=None,
        price_to_sales=price_to_sales,
        debt_to_equity=_debt_equity(debt, equity),
        roe=_ratio(income, equity[-1][1] if equity else 0),
        roic=None,
        next_earnings=None,
        shares_outstanding=_shares(facts),
        data_mode="live",
        source="sec-edgar",
    )


def filed_fundamental(ticker: str) -> Fundamentals | None:
    if _cache is None:
        return None
    return _cache.get(ticker.upper())


def ensure_fundamental(ticker: str, price: Decimal | None = None) -> Fundamentals | None:
    global _cache
    symbol = ticker.upper()
    cached = None if _cache is None else _cache.get(symbol)
    if cached is not None and cached.eps and price is not None and cached.pe is None:
        updated = cached.model_copy(update={"pe": round(float(price) / float(cached.eps), 2)})
        _cache[symbol] = updated
        return updated
    if cached is not None:
        return cached
    cik = cik_for(symbol)
    if cik is None:
        return None
    try:
        facts = _download(cik)
    except (OSError, ValueError, TimeoutError, json.JSONDecodeError):
        return None
    row = build_fundamentals(symbol, facts, price)
    if row is None:
        return None
    if _cache is None:
        _cache = {}
    _cache[symbol] = row
    return row


def cik_for(ticker: str) -> str | None:
    symbol = ticker.upper()
    if symbol in CIKS:
        return CIKS[symbol]
    from meridian_market.symbols import get_directory

    listing = get_directory().lookup(symbol)
    return None if listing is None else listing.cik


def recent_filings(ticker: str, limit: int = 8) -> list[Filing]:
    symbol = ticker.upper()
    cached = _filing_cache.get(symbol)
    if cached is not None:
        return cached[:limit]
    cik = cik_for(symbol)
    if cik is None:
        return []
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (OSError, ValueError, TimeoutError, json.JSONDecodeError):
        return []
    rows = parse_filings(payload, cik)
    _filing_cache[symbol] = rows
    return rows[:limit]


def parse_filings(payload: dict, cik: str) -> list[Filing]:
    recent = (payload.get("filings") or {}).get("recent") or {}
    forms = recent.get("form") or []
    dates = recent.get("filingDate") or []
    accessions = recent.get("accessionNumber") or []
    documents = recent.get("primaryDocument") or []
    descriptions = recent.get("primaryDocDescription") or []
    cik_int = str(int(cik))
    limits = {"10-K": 1, "10-K/A": 1, "10-Q": 2, "10-Q/A": 1, "8-K": 3, "4": 2}
    chosen: dict[str, list[Filing]] = {form: [] for form in limits}
    for index, form in enumerate(forms):
        form = str(form)
        if form not in limits or len(chosen[form]) >= limits[form]:
            continue
        if index >= len(dates) or index >= len(accessions) or index >= len(documents):
            continue
        document = str(documents[index])
        if not document:
            continue
        accession = str(accessions[index]).replace("-", "")
        description = str(descriptions[index]) if index < len(descriptions) and descriptions[index] else form
        chosen[form].append(
            Filing(
                form=form,
                filed_on=date.fromisoformat(str(dates[index])),
                description=description,
                url=f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession}/{document}",
            )
        )
    rows = [item for group in chosen.values() for item in group]
    rows.sort(key=lambda item: item.filed_on, reverse=True)
    return rows


def load_sec_fundamentals(price_for: dict[str, Decimal] | None = None) -> dict[str, Fundamentals]:
    global _cache
    if _cache is not None and price_for is None:
        return _cache
    downloaded: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_download, cik): ticker for ticker, cik in CIKS.items()}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                downloaded[ticker] = future.result()
            except (OSError, ValueError, TimeoutError, json.JSONDecodeError):
                continue
    built: dict[str, Fundamentals] = {}
    for ticker, facts in downloaded.items():
        price = None if price_for is None else price_for.get(ticker)
        row = build_fundamentals(ticker, facts, price)
        if row is not None:
            built[ticker] = row
    if price_for is None:
        _cache = built
    return built


def _download(cik: str) -> dict:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    return payload.get("facts", {})


def _shares(facts: dict) -> int | None:
    rows = (
        facts.get("dei", {})
        .get("EntityCommonStockSharesOutstanding", {})
        .get("units", {})
        .get("shares", [])
    )
    dated = [row for row in rows if row.get("val")]
    if not dated:
        return None
    dated.sort(key=lambda row: str(row.get("end", "")))
    return int(dated[-1]["val"])


def _growth(series: list[tuple[str, float]]) -> float:
    if len(series) < 2 or series[-2][1] == 0:
        return 0.0
    return (series[-1][1] - series[-2][1]) / abs(series[-2][1])


def _ratio(series: list[tuple[str, float]], base: float) -> float:
    if not series or not base:
        return 0.0
    return series[-1][1] / base


def _debt_equity(debt: list[tuple[str, float]], equity: list[tuple[str, float]]) -> float | None:
    if not debt or not equity or equity[-1][1] == 0:
        return None
    return debt[-1][1] / equity[-1][1]
