from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from meridian_market.symbols import get_directory
from meridian_research.providers import bundle_for

from meridian_api.gateway import active_book, data_status

router = APIRouter(prefix="/api/v1")


def _unknown(ticker: str, exc: KeyError) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Unknown ticker {ticker}")


@router.get("/symbols")
def symbols(q: str = Query(default="", max_length=80)) -> dict[str, object]:
    matches = get_directory().search(q, limit=8)
    return {
        "query": q.strip(),
        "matches": [{"ticker": row.ticker, "name": row.name, "cik": row.cik} for row in matches],
    }


@router.get("/market/quotes")
def quotes() -> dict[str, object]:
    book = active_book()
    status = data_status()
    return {
        "dataMode": status["dataMode"],
        "source": status["source"],
        "warning": status["warning"],
        "quotes": [row.model_dump(mode="json", by_alias=True) for row in book.quotes()],
    }


@router.get("/market/quotes/{ticker}")
def quote(ticker: str) -> dict[str, object]:
    book = active_book()
    try:
        row = book.quote(ticker)
    except KeyError as exc:
        raise _unknown(ticker, exc) from exc
    return row.model_dump(mode="json", by_alias=True)


@router.get("/market/history/{ticker}")
def history(ticker: str, limit: int = Query(default=180, ge=2, le=320)) -> dict[str, object]:
    book = active_book()
    status = data_status()
    try:
        bars = book.bars(ticker)
    except KeyError as exc:
        raise _unknown(ticker, exc) from exc
    return {
        "ticker": ticker.upper(),
        "dataMode": status["dataMode"],
        "bars": [bar.model_dump(mode="json", by_alias=True) for bar in bars[-limit:]],
    }


@router.get("/market/fundamentals/{ticker}")
def fundamental(ticker: str) -> dict[str, object]:
    book = active_book()
    try:
        row = book.fundamentals(ticker)
    except KeyError as exc:
        raise _unknown(ticker, exc) from exc
    return row.model_dump(mode="json", by_alias=True)


@router.get("/market/technicals/{ticker}")
def technical(ticker: str) -> dict[str, object]:
    book = active_book()
    try:
        row = book.technicals(ticker)
    except KeyError as exc:
        raise _unknown(ticker, exc) from exc
    return row.model_dump(mode="json", by_alias=True)


@router.get("/market/indexes")
def indexes() -> dict[str, object]:
    book = active_book()
    status = data_status()
    return {
        "dataMode": status["dataMode"],
        "indexes": [row.model_dump(mode="json", by_alias=True) for row in book.index_quotes()],
    }


@router.get("/market/sentiment")
def sentiment() -> dict[str, object]:
    return active_book().sentiment().model_dump(mode="json", by_alias=True)


@router.get("/research/{ticker}")
def research(ticker: str) -> dict[str, object]:
    book = active_book()
    try:
        book.require(ticker)
        bundle = bundle_for(ticker, book)
    except KeyError as exc:
        raise _unknown(ticker, exc) from exc
    return bundle.model_dump(mode="json", by_alias=True)
