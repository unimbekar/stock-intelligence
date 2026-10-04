from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException
from meridian_db.models import (
    Alert,
    AuditLog,
    JournalEntry,
    Portfolio,
    SavedIdea,
    ScoringProfile,
    Transaction,
    User,
    UserPreference,
    Watchlist,
    WatchlistItem,
)
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from meridian_api.deps import admin_user, current_user, db_session
from meridian_api.gateway import active_book, data_status
from meridian_api.mail import deliverable, recipient, send_mail, smtp_ready
from meridian_api.portfolio_view import (
    build_workspace,
    money,
    percent_target,
    plan_holding_change,
    propose_trade,
    scanner_rows,
    search,
    size_plan,
)

router = APIRouter(prefix="/api/v1")


class PreferenceBody(BaseModel):
    capital: Decimal = Field(gt=0)
    dailyProfitTarget: Decimal = Field(ge=0)
    tradingStyle: str
    riskTolerance: str
    sectors: list[str] = []
    experience: str = "intermediate"
    goals: str = ""
    onboardingCompleted: bool = True
    maxPositionPct: Decimal = Field(gt=0, le=100)
    maxSectorPct: Decimal = Field(gt=0, le=100)
    maxRiskPerTradePct: Decimal = Field(gt=0, le=100)
    maxDailyLoss: Decimal = Field(gt=0)
    maxOpenPositions: int = Field(ge=1, le=50)


class WatchlistBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""


class WatchItemBody(BaseModel):
    ticker: str
    notes: str = ""
    priority: str = "medium"
    targetPrice: Decimal | None = None


class AlertBody(BaseModel):
    ticker: str
    alertType: str
    params: dict
    enabled: bool = True


class AlertUpdate(BaseModel):
    ticker: str | None = None
    alertType: str | None = None
    params: dict | None = None
    enabled: bool | None = None


class DestinationBody(BaseModel):
    email: str = ""


class JournalBody(BaseModel):
    ticker: str
    entryThesis: str = ""
    exitThesis: str = ""
    strategy: str = ""
    marketConditions: str = ""
    emotion: str = ""
    notes: str = ""
    screenshotPath: str | None = None
    openedAt: datetime | None = None
    closedAt: datetime | None = None


class HoldingBody(BaseModel):
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)


class CashBody(BaseModel):
    amount: Decimal = Field(gt=0, le=Decimal("100000000"))


class TradeBody(BaseModel):
    ticker: str
    side: str
    quantity: Decimal = Field(gt=0)
    price: Decimal | None = None
    fees: Decimal = Field(default=Decimal("0"), ge=0)
    notes: str = ""
    strategy: str = ""


class SizeBody(BaseModel):
    account: Decimal = Field(gt=0)
    riskPercent: Decimal = Field(gt=0, le=100)
    entry: Decimal = Field(gt=0)
    stop: Decimal = Field(gt=0)
    target: Decimal | None = None


class IdeaQuery(BaseModel):
    query: str = ""
    sector: str = ""
    categories: list[str] = []
    minMarketCap: int | None = None
    maxMarketCap: int | None = None
    minVolume: int | None = None
    maxVolatility: float | None = None
    minPrice: float | None = None
    maxPrice: float | None = None
    analyst: str | None = None
    exclude: list[str] = []
    style: str | None = None
    risk: str | None = None
    amount: Decimal | None = None


class SaveIdeaBody(BaseModel):
    ticker: str
    title: str
    payload: dict


class WeightsBody(BaseModel):
    technicalMomentum: float
    fundamentalStrength: float
    analystSentiment: float
    earningsMomentum: float
    valuation: float
    sectorMomentum: float
    riskVolatility: float


def _audit(db: Session, user: User, action: str, resource: str, resource_id: str) -> None:
    db.add(AuditLog(user_id=user.id, action=action, resource=resource, resource_id=resource_id, detail={}))


def _prepare_alert_params(ticker: str, alert_type: str, params: dict) -> dict:
    if alert_type not in {"price", "percent", "rsi", "volume"}:
        raise HTTPException(status_code=400, detail="Alert type must be price, percent, rsi, or volume.")
    email = bool(params.get("email", True))
    direction = str(params.get("direction", "above"))
    try:
        if alert_type == "price":
            if direction not in {"above", "below"}:
                raise ValueError("Direction must be above or below.")
            price = Decimal(str(params.get("price", "0")))
            if price <= 0:
                raise ValueError("Price must be positive.")
            return {"direction": direction, "price": float(price), "email": email}
        if alert_type == "percent":
            percent = Decimal(str(params.get("percent", "0")))
            quote = active_book().quote(ticker)
            target = percent_target(quote.price, percent, direction)
            return {
                "direction": direction,
                "percent": float(percent),
                "basis": money(quote.price),
                "target": money(target),
                "email": email,
            }
        if alert_type == "rsi":
            if direction not in {"above", "below"}:
                raise ValueError("Direction must be above or below.")
            level = Decimal(str(params.get("level", "0")))
            if level <= 0 or level > 100:
                raise ValueError("RSI level must be greater than 0 and at most 100.")
            return {"direction": direction, "level": float(level), "email": email}
        relative = Decimal(str(params.get("relativeVolume", "0")))
        if relative <= 0:
            raise ValueError("Relative volume must be positive.")
        return {"relativeVolume": float(relative), "email": email}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="No session price is available for this symbol.") from exc
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "Alert could not be saved.") from exc


def _known(ticker: str) -> str:
    book = active_book()
    symbol = ticker.strip().upper()
    if _listed(book, symbol):
        return symbol
    from meridian_market.symbols import get_directory

    match = next(iter(get_directory().search(symbol, limit=1)), None)
    if match is not None and (match.ticker == symbol or symbol in match.name.upper()):
        if _listed(book, match.ticker):
            return match.ticker
    raise HTTPException(status_code=404, detail=f"No listing with session history was found for {ticker}.")


def _listed(book, symbol: str) -> bool:
    try:
        book.require(symbol)
    except KeyError:
        return False
    return True


def _portfolio(db: Session, user: User) -> Portfolio:
    portfolio = db.scalar(
        select(Portfolio).where(Portfolio.user_id == user.id, Portfolio.is_default.is_(True))
    )
    if portfolio is None:
        raise HTTPException(status_code=404, detail="No portfolio is available.")
    return portfolio


@router.get("/workspace")
def workspace(user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    try:
        return build_workspace(db, user)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Workspace is not ready.") from exc


@router.patch("/preferences")
def update_preferences(
    body: PreferenceBody,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> dict:
    preference = db.get(UserPreference, user.id)
    if preference is None:
        raise HTTPException(status_code=404, detail="Preferences were not found.")
    preference.capital = body.capital
    preference.daily_profit_target = body.dailyProfitTarget
    preference.trading_style = body.tradingStyle
    preference.risk_tolerance = body.riskTolerance
    preference.sectors = body.sectors
    preference.experience = body.experience
    preference.goals = body.goals
    preference.onboarding_completed = body.onboardingCompleted
    preference.max_position_pct = body.maxPositionPct
    preference.max_sector_pct = body.maxSectorPct
    preference.max_risk_per_trade_pct = body.maxRiskPerTradePct
    preference.max_daily_loss = body.maxDailyLoss
    preference.max_open_positions = body.maxOpenPositions
    _audit(db, user, "update", "preferences", str(user.id))
    return {"status": "saved"}


@router.post("/watchlists")
def create_watchlist(
    body: WatchlistBody,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> dict:
    row = Watchlist(user_id=user.id, name=body.name.strip(), description=body.description)
    db.add(row)
    db.flush()
    _audit(db, user, "create", "watchlist", str(row.id))
    return {"id": str(row.id)}


@router.delete("/watchlists/{watchlist_id}")
def delete_watchlist(
    watchlist_id: uuid.UUID,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> dict:
    row = db.get(Watchlist, watchlist_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Watchlist was not found.")
    db.delete(row)
    _audit(db, user, "delete", "watchlist", str(watchlist_id))
    return {"status": "deleted"}


@router.post("/watchlists/{watchlist_id}/items")
def add_watch_item(
    watchlist_id: uuid.UUID,
    body: WatchItemBody,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> dict:
    row = db.get(Watchlist, watchlist_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Watchlist was not found.")
    ticker = _known(body.ticker)
    existing = db.scalar(
        select(WatchlistItem).where(WatchlistItem.watchlist_id == row.id, WatchlistItem.ticker == ticker)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"{ticker} is already on this list.")
    order = db.scalar(select(func.count()).select_from(WatchlistItem).where(WatchlistItem.watchlist_id == row.id)) or 0
    db.add(
        WatchlistItem(
            watchlist_id=row.id,
            ticker=ticker,
            notes=body.notes,
            priority=body.priority,
            target_price=body.targetPrice,
            sort_order=int(order),
        )
    )
    return {"status": "added"}


@router.delete("/watchlists/{watchlist_id}/items/{ticker}")
def remove_watch_item(
    watchlist_id: uuid.UUID,
    ticker: str,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> dict:
    row = db.get(Watchlist, watchlist_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Watchlist was not found.")
    item = db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == row.id,
            WatchlistItem.ticker == ticker.upper(),
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Ticker was not found on this list.")
    db.delete(item)
    return {"status": "removed"}


@router.patch("/alerts/destination")
def set_alert_destination(
    body: DestinationBody,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> dict:
    preference = db.get(UserPreference, user.id)
    if preference is None:
        raise HTTPException(status_code=404, detail="Preferences were not found.")
    address = body.email.strip()
    if address and not deliverable(address):
        raise HTTPException(status_code=400, detail="Enter an email address that can receive mail.")
    preference.notify_email = address
    return {"address": address, "configured": smtp_ready()}


@router.post("/alerts/test-email")
def test_alert_email(user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    preference = db.get(UserPreference, user.id)
    address = recipient(user, preference)
    if not address:
        raise HTTPException(status_code=400, detail="Save an email address that can receive mail.")
    if not smtp_ready():
        raise HTTPException(
            status_code=400,
            detail="Set SMTP_HOST and SMTP_FROM in the API environment before mail can be sent.",
        )
    subject = "Meridian alert mail is working"
    body = (
        "Meridian can reach this address.\n\n"
        "Price alerts use the last Nasdaq regular session, not a live quote. "
        "This note is not a recommendation to buy or sell."
    )
    if not send_mail(address, subject, body):
        raise HTTPException(status_code=502, detail="The mail server did not accept the message.")
    return {"status": "sent", "address": address}


@router.post("/alerts")
def create_alert(body: AlertBody, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    ticker = _known(body.ticker)
    params = _prepare_alert_params(ticker, body.alertType, body.params)
    row = Alert(user_id=user.id, ticker=ticker, alert_type=body.alertType, params=params, enabled=body.enabled)
    db.add(row)
    db.flush()
    return {"id": str(row.id)}


@router.patch("/alerts/{alert_id}")
def update_alert(
    alert_id: uuid.UUID,
    body: AlertUpdate | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> dict:
    row = db.get(Alert, alert_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Alert was not found.")
    if body is None or not body.model_fields_set:
        row.enabled = not row.enabled
        if row.enabled:
            row.notified = False
        return {"enabled": row.enabled}
    if body.ticker is not None or body.alertType is not None or body.params is not None:
        ticker = _known(body.ticker) if body.ticker is not None else (row.ticker or "")
        kind = body.alertType or row.alert_type
        params = body.params if body.params is not None else dict(row.params or {})
        row.ticker = ticker
        row.alert_type = kind
        row.params = _prepare_alert_params(ticker, kind, params)
        row.notified = False
    if body.enabled is not None:
        row.enabled = body.enabled
        if body.enabled:
            row.notified = False
    return {"status": "saved"}


@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    row = db.get(Alert, alert_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Alert was not found.")
    db.delete(row)
    return {"status": "deleted"}


@router.post("/journal")
def create_journal(body: JournalBody, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    ticker = _known(body.ticker)
    portfolio = _portfolio(db, user)
    row = JournalEntry(
        user_id=user.id,
        portfolio_id=portfolio.id,
        ticker=ticker,
        entry_thesis=body.entryThesis,
        exit_thesis=body.exitThesis,
        strategy=body.strategy,
        market_conditions=body.marketConditions,
        emotion=body.emotion,
        notes=body.notes,
        screenshot_path=body.screenshotPath,
        opened_at=body.openedAt,
        closed_at=body.closedAt,
    )
    db.add(row)
    db.flush()
    return {"id": str(row.id)}


@router.patch("/journal/{entry_id}")
def update_journal(
    entry_id: uuid.UUID,
    body: JournalBody,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> dict:
    row = db.get(JournalEntry, entry_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Journal entry was not found.")
    row.ticker = _known(body.ticker)
    row.entry_thesis = body.entryThesis
    row.exit_thesis = body.exitThesis
    row.strategy = body.strategy
    row.market_conditions = body.marketConditions
    row.emotion = body.emotion
    row.notes = body.notes
    row.screenshot_path = body.screenshotPath
    row.opened_at = body.openedAt
    row.closed_at = body.closedAt
    return {"status": "saved"}


@router.delete("/journal/{entry_id}")
def delete_journal(entry_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    row = db.get(JournalEntry, entry_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Journal entry was not found.")
    db.delete(row)
    return {"status": "deleted"}


@router.patch("/watchlists/{watchlist_id}")
def rename_watchlist(
    watchlist_id: uuid.UUID,
    body: WatchlistBody,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> dict:
    row = db.get(Watchlist, watchlist_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Watchlist was not found.")
    row.name = body.name.strip()
    row.description = body.description or row.description
    try:
        db.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="You already have a list with that name.") from exc
    return {"status": "saved"}


@router.patch("/portfolio/holdings/{ticker}")
def update_holding(
    ticker: str,
    body: HoldingBody,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> dict:
    portfolio = _portfolio(db, user)
    _record_holding_change(db, user, portfolio, ticker, body.quantity, body.price)
    return {"status": "updated", "cash": money(portfolio.cash)}


@router.delete("/portfolio/holdings/{ticker}")
def delete_holding(
    ticker: str,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> dict:
    portfolio = _portfolio(db, user)
    _record_holding_change(db, user, portfolio, ticker, Decimal("0"), Decimal("0"))
    return {"status": "deleted", "cash": money(portfolio.cash)}


def _record_holding_change(
    db: Session,
    user: User,
    portfolio: Portfolio,
    ticker: str,
    quantity: Decimal,
    price: Decimal,
) -> None:
    try:
        delta, orders = plan_holding_change(portfolio, ticker, quantity, price)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    portfolio.cash = (portfolio.cash + delta).quantize(Decimal("0.01"))
    stamp = datetime.now(UTC)
    symbol = ticker.strip().upper()
    for index, order in enumerate(orders):
        db.add(
            Transaction(
                portfolio_id=portfolio.id,
                ticker=symbol,
                side=str(order["side"]),
                quantity=Decimal(order["quantity"]),
                price=Decimal(order["price"]),
                fees=Decimal("0"),
                executed_at=stamp + timedelta(microseconds=index),
                notes=str(order["notes"]),
                strategy="edit",
            )
        )
    _audit(db, user, "update" if quantity > 0 else "delete", "holding", symbol)


@router.post("/portfolio/cash")
def add_cash(body: CashBody, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    portfolio = _portfolio(db, user)
    portfolio.cash = (portfolio.cash + body.amount).quantize(Decimal("0.01"))
    _audit(db, user, "deposit", "portfolio", str(portfolio.id))
    return {"cash": money(portfolio.cash)}


@router.post("/trades")
def trade(body: TradeBody, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    if body.side not in {"buy", "sell", "short", "cover"}:
        raise HTTPException(status_code=400, detail="Side must be buy, sell, short, or cover.")
    ticker = _known(body.ticker)
    book = active_book()
    price = body.price if body.price is not None else book.quote(ticker).price
    if price <= 0:
        raise HTTPException(status_code=400, detail="Price must be positive.")
    portfolio = _portfolio(db, user)
    try:
        propose_trade(portfolio, book, ticker, body.side, body.quantity, price, body.fees)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    from meridian_analytics.snapshot import cash_delta

    portfolio.cash = (portfolio.cash + cash_delta(body.side, body.quantity, price, body.fees)).quantize(Decimal("0.01"))
    db.add(
        Transaction(
            portfolio_id=portfolio.id,
            ticker=ticker,
            side=body.side,
            quantity=body.quantity,
            price=price,
            fees=body.fees,
            executed_at=datetime.now(UTC),
            notes=body.notes or "Paper order.",
            strategy=body.strategy,
        )
    )
    _audit(db, user, "trade", "portfolio", str(portfolio.id))
    return {"status": "filled", "price": money(price), "cash": money(portfolio.cash)}


@router.post("/position-size")
def position_size(body: SizeBody, user: User = Depends(current_user)) -> dict:
    del user
    try:
        return size_plan(body.account, body.riskPercent, body.entry, body.stop, body.target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ideas/search")
def ideas(body: IdeaQuery, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    return search(body.model_dump(), user, db)


@router.post("/scanner")
def scan(body: IdeaQuery, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    del user
    return scanner_rows(body.model_dump(), db)


@router.post("/ideas")
def save_idea(body: SaveIdeaBody, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    ticker = _known(body.ticker)
    row = SavedIdea(user_id=user.id, ticker=ticker, title=body.title[:200], payload=body.payload)
    db.add(row)
    db.flush()
    return {"id": str(row.id)}


class IdeaTitleBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@router.patch("/ideas/{idea_id}")
def update_idea(
    idea_id: uuid.UUID,
    body: IdeaTitleBody,
    user: User = Depends(current_user),
    db: Session = Depends(db_session),
) -> dict:
    row = db.get(SavedIdea, idea_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Saved idea was not found.")
    row.title = body.title.strip()[:200]
    return {"status": "saved"}


@router.delete("/ideas/{idea_id}")
def delete_idea(idea_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(db_session)) -> dict:
    row = db.get(SavedIdea, idea_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Saved idea was not found.")
    db.delete(row)
    return {"status": "deleted"}


@router.get("/admin/summary")
def admin_summary(user: User = Depends(admin_user), db: Session = Depends(db_session)) -> dict:
    users = db.scalar(select(func.count()).select_from(User)) or 0
    logs = list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(20)))
    profile = db.scalar(select(ScoringProfile).where(ScoringProfile.is_active.is_(True)))
    return {
        "users": int(users),
        "weights": profile.weights if profile else {},
        "data": data_status(),
        "actor": user.email,
        "audit": [
            {
                "action": log.action,
                "resource": log.resource,
                "createdAt": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }


@router.put("/admin/weights")
def update_weights(
    body: WeightsBody,
    user: User = Depends(admin_user),
    db: Session = Depends(db_session),
) -> dict:
    values = body.model_dump()
    total = sum(values.values())
    if abs(total - 1) > 0.001:
        raise HTTPException(status_code=400, detail="Scoring weights must sum to 1.")
    profile = db.scalar(select(ScoringProfile).where(ScoringProfile.is_active.is_(True)))
    if profile is None:
        profile = ScoringProfile(name="Default", weights=values, is_active=True)
        db.add(profile)
    else:
        profile.weights = values
    _audit(db, user, "update", "scoring_profile", profile.name)
    return {"status": "saved", "weights": values}
