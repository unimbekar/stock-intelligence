from __future__ import annotations

from fastapi import APIRouter, Depends
from meridian_ai import TOOLS, AIMessage, build_provider
from meridian_config.settings import get_settings
from meridian_db.models import User
from meridian_market.symbols import get_directory, mentioned_symbols
from meridian_research.providers import bundle_for
from meridian_trading.sizing import plan_position
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from meridian_api.deps import current_user, db_session
from meridian_api.gateway import active_book
from meridian_api.portfolio_view import build_workspace

router = APIRouter(prefix="/api/v1")


class AskBody(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@router.post("/assistant")
def ask(body: AskBody, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    book = active_book()
    mentioned = mentioned_symbols(body.question, set(book.instruments), get_directory())
    if not mentioned:
        mentioned = ["NVDA"]
    loaded = [symbol for symbol in mentioned if _loadable(book, symbol)]
    if not loaded:
        return {
            "content": (
                f"No Nasdaq session history was found for {', '.join(mentioned)}. "
                "Nothing was substituted."
            ),
            "provider": "local",
            "model": get_settings().local_ai_model or "offline-explainer",
            "usedTools": [],
            "availableTools": TOOLS,
            "disclaimer": (
                "The assistant restates tool output. It does not invent quotes, filings, or profit targets, "
                "and it is not investment advice."
            ),
        }
    tools = _tools(body.question, loaded, book, user, db)
    provider = build_provider(get_settings())
    answer = provider.complete([AIMessage(role="user", content=body.question)], tools)
    return {
        "content": answer.content,
        "provider": answer.provider,
        "model": answer.model,
        "usedTools": answer.used_tools,
        "availableTools": TOOLS,
        "disclaimer": (
            "The assistant restates tool output. It does not invent quotes, filings, or profit targets, "
            "and it is not investment advice."
        ),
    }


def _loadable(book, symbol: str) -> bool:
    try:
        book.require(symbol)
    except KeyError:
        return False
    return True


def _tools(question: str, tickers: list[str], book, user: User, db: Session) -> dict[str, object]:
    symbol = tickers[0]
    quote = book.quote(symbol).model_dump(mode="json", by_alias=True)
    history = [bar.model_dump(mode="json", by_alias=True) for bar in book.bars(symbol)[-5:]]
    fundamentals = book.fundamentals(symbol).model_dump(mode="json", by_alias=True)
    technicals = book.technicals(symbol).model_dump(mode="json", by_alias=True)
    bundle = bundle_for(symbol, book).model_dump(mode="json", by_alias=True)
    workspace = build_workspace(db, user)
    portfolio = workspace.get("portfolio") or {}
    lowered = question.lower()
    tools: dict[str, object] = {
        "get_stock_quote": quote,
        "get_historical_prices": {"ticker": symbol, "bars": history},
        "get_fundamentals": fundamentals,
        "get_technical_indicators": technicals,
        "get_news": [item for item in bundle["items"] if item.get("sourceType") == "news"],
        "get_research": [item for item in bundle["items"] if item.get("sourceType") != "news"],
        "get_analyst_ratings": bundle["consensus"],
        "get_portfolio": {
            "cash": portfolio.get("cash"),
            "equity": portfolio.get("equity"),
            "dailyPnl": portfolio.get("dailyPnl"),
        },
        "get_positions": portfolio.get("positions", []),
        "get_watchlist": workspace.get("watchlists", []),
    }
    if "size" in lowered or "risk" in lowered or "stop" in lowered:
        preference = workspace["preference"]
        entry = book.quote(symbol).price
        atr = technicals.get("atr")
        if atr:
            stop = entry - entry.__class__(str(atr))
            if stop > 0 and stop < entry:
                plan = plan_position(
                    account=user.preference.capital if user.preference else entry,
                    risk_percent=user.preference.max_risk_per_trade_pct if user.preference else entry.__class__("1"),
                    entry=entry,
                    stop=stop,
                )
                tools["calculate_position_size"] = {
                    "shares": str(plan.shares),
                    "maxRisk": str(plan.max_risk),
                    "entry": str(plan.entry),
                    "stop": str(plan.stop),
                }
                tools["calculate_risk"] = {
                    "riskPerShare": str(plan.risk_per_share),
                    "positionValue": str(plan.position_value),
                    "preference": preference,
                }
    tools["calculate_portfolio_metrics"] = portfolio.get("performance", {})
    return tools
