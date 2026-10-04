"""Assemble one JSON workspace from the ledger and the active market book."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from meridian_analytics.ledger import Fill, apply_fills
from meridian_analytics.performance import expectancy, max_drawdown, profit_factor, sharpe, sortino, win_rate
from meridian_analytics.scoring import IdeaFilters, component_scores, composite
from meridian_analytics.snapshot import cash_delta, closing_pnls, equity_curve, holding_rating, pearson, position_view
from meridian_config.product import load_product
from meridian_config.settings import get_settings
from meridian_db.models import Alert, JournalEntry, Portfolio, SavedIdea, ScoringProfile, User, Watchlist
from meridian_trading.sizing import daily_loss_status, plan_position, required_return
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from meridian_api.gateway import active_book, data_status
from meridian_api.ideas_service import build_inputs, search_ideas

MONEY = Decimal("0.01")


def money(value: Decimal) -> str:
    return format(value.quantize(MONEY), "f")


def _level(value: float | None) -> str | None:
    if value is None:
        return None
    return money(Decimal(str(value)))


def build_workspace(db: Session, user: User) -> dict[str, object]:
    book = active_book()
    status = data_status()
    loaded = db.scalar(
        select(User)
        .where(User.id == user.id)
        .options(
            selectinload(User.preference),
            selectinload(User.portfolios).selectinload(Portfolio.transactions),
            selectinload(User.watchlists).selectinload(Watchlist.items),
        )
    )
    if loaded is None or loaded.preference is None:
        raise LookupError("user")
    preference = loaded.preference
    portfolio = next((item for item in loaded.portfolios if item.is_default), None)
    if portfolio is None and loaded.portfolios:
        portfolio = loaded.portfolios[0]
    alerts = list(db.scalars(select(Alert).where(Alert.user_id == user.id).order_by(Alert.created_at)))
    journal = list(
        db.scalars(select(JournalEntry).where(JournalEntry.user_id == user.id).order_by(JournalEntry.created_at.desc()))
    )
    saved_query = select(SavedIdea).where(SavedIdea.user_id == user.id).order_by(SavedIdea.created_at.desc())
    saved = list(db.scalars(saved_query))
    profile = db.scalar(select(ScoringProfile).where(ScoringProfile.is_active.is_(True)))
    weights = profile.weights if profile else load_product().scoring_weights.model_dump(by_alias=True)
    snapshot = _portfolio(portfolio, book, preference) if portfolio else None
    triggered = evaluate_alerts(alerts, book)
    quotes = [row.model_dump(mode="json", by_alias=True) for row in book.quotes()]
    settings = get_settings()
    return {
        "user": {
            "id": str(loaded.id),
            "email": loaded.email,
            "displayName": loaded.display_name,
            "role": loaded.role,
        },
        "data": status,
        "preference": _preference(preference),
        "weights": weights,
        "portfolio": snapshot,
        "quotes": quotes,
        "indexes": [row.model_dump(mode="json", by_alias=True) for row in book.index_quotes()],
        "sentiment": book.sentiment().model_dump(mode="json", by_alias=True),
        "watchlists": [
            _watchlist(item, {row["ticker"]: row for row in quotes}, book) for item in loaded.watchlists
        ],
        "mail": {
            "address": preference.notify_email or "",
            "configured": bool(settings.smtp_host.strip() and settings.smtp_from.strip()),
        },
        "alerts": [_alert(item, triggered.get(item.id, False), book) for item in alerts],
        "journal": [_journal(item) for item in journal],
        "savedIdeas": [_saved(item) for item in saved],
        "asOf": book.as_of.isoformat(),
    }


def search(user_filters: dict, user: User, db: Session) -> dict[str, object]:
    book = active_book()
    preference = user.preference
    if preference is None:
        raise LookupError("preference")
    profile = db.scalar(select(ScoringProfile).where(ScoringProfile.is_active.is_(True)))
    weights_raw = profile.weights if profile else load_product().scoring_weights.model_dump(by_alias=True)
    weights = _weight_fractions(weights_raw)
    filters = IdeaFilters(
        categories=tuple(user_filters.get("categories") or ()),
        min_market_cap=_optional_int(user_filters.get("minMarketCap")),
        max_market_cap=_optional_int(user_filters.get("maxMarketCap")),
        min_volume=_optional_int(user_filters.get("minVolume")),
        max_volatility=_optional_float(user_filters.get("maxVolatility")),
        min_price=_optional_float(user_filters.get("minPrice")),
        max_price=_optional_float(user_filters.get("maxPrice")),
        analyst=user_filters.get("analyst") or None,
        exclude=tuple(str(ticker).upper() for ticker in user_filters.get("exclude") or []),
    )
    style = str(user_filters.get("style") or preference.trading_style)
    risk = str(user_filters.get("risk") or preference.risk_tolerance)
    amount = Decimal(str(user_filters.get("amount") or preference.capital))
    return search_ideas(book, amount=amount, style=style, risk=risk, filters=filters, weights=weights)


def scanner_rows(filters: dict, db: Session) -> dict[str, object]:
    book = active_book()
    profile = db.scalar(select(ScoringProfile).where(ScoringProfile.is_active.is_(True)))
    raw_weights = profile.weights if profile else load_product().scoring_weights.model_dump(by_alias=True)
    weights = _weight_fractions(raw_weights)
    query = (filters.get("query") or "").strip().lower()
    sector = filters.get("sector") or ""
    rows = []
    for item in build_inputs(book):
        if query and query not in item.ticker.lower() and query not in item.company.lower():
            continue
        if sector and sector != "All" and item.sector != sector:
            continue
        if filters.get("minMarketCap") and item.market_cap < int(filters["minMarketCap"]):
            continue
        if filters.get("minVolume") and item.volume < int(filters["minVolume"]):
            continue
        parts = component_scores(item)
        rows.append(
            {
                "ticker": item.ticker,
                "company": item.company,
                "sector": item.sector,
                "price": f"{item.price:.2f}",
                "marketCap": item.market_cap,
                "volume": item.volume,
                "rsi": item.rsi,
                "pe": item.pe,
                "relativeVolume": item.relative_volume,
                "analyst": item.analyst,
                "score": composite(parts, weights),
                "parts": parts,
            }
        )
    rows.sort(key=lambda row: (-float(row["score"]), row["ticker"]))
    return {"dataMode": getattr(book, "data_mode", "mock"), "rows": rows}


def _portfolio(portfolio: Portfolio, book, preference) -> dict[str, object]:
    ordered = sorted(portfolio.transactions, key=lambda item: item.executed_at)
    fills = [_fill(item) for item in ordered]
    marks = {}
    quote_by_ticker = {}
    for ticker in {fill.ticker.upper() for fill in fills}:
        try:
            quote = book.quote(ticker)
        except KeyError:
            continue
        quote_by_ticker[ticker] = quote
        marks[ticker] = (quote.price, quote.price - quote.change, quote.sector or "Unclassified")
    positions = position_view(fills, marks) if fills else []
    market_value = sum((row["market_value"] for row in positions), Decimal("0"))
    equity = portfolio.cash + market_value
    daily = sum((row["daily_pnl"] for row in positions), Decimal("0"))
    unrealized = sum((row["unrealized_pnl"] for row in positions), Decimal("0"))
    realized = sum((row["realized_pnl"] for row in positions), Decimal("0"))
    day_return = (daily / (equity - daily) * Decimal("100")) if equity != daily else Decimal("0")
    if preference.capital:
        total_return = (equity - preference.capital) / preference.capital * Decimal("100")
    else:
        total_return = Decimal("0")
    closes = {ticker: {bar.session: bar.close for bar in book.bars(ticker)} for ticker in marks}
    curve = equity_curve([(item.executed_at.date(), _fill(item)) for item in ordered], portfolio.cash, closes)
    returns = []
    for previous, current in zip(curve, curve[1:], strict=False):
        if previous[1] != 0:
            returns.append((current[1] - previous[1]) / previous[1])
    trade_pnls = closing_pnls(fills)
    sectors: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in positions:
        sectors[str(row["sector"])] += row["market_value"]
    open_count = len(positions)
    largest = max((abs(row["market_value"]) for row in positions), default=Decimal("0"))
    largest_pct = (largest / equity * Decimal("100")) if equity else Decimal("0")
    sector_pcts = {
        name: (value / equity * Decimal("100")) if equity else Decimal("0") for name, value in sectors.items()
    }
    hottest = max(sector_pcts, key=sector_pcts.get) if sector_pcts else None
    loss_today = -daily if daily < 0 else Decimal("0")
    betas = []
    for row in positions:
        instrument = book.instruments.get(str(row["ticker"]))
        if instrument is None or equity == 0:
            continue
        weight = row["market_value"] / equity
        betas.append(weight * Decimal(str(instrument.beta)))
    correlations = _correlations(positions, closes, book)
    rendered_positions = []
    for row in positions:
        value = row["market_value"]
        ticker = str(row["ticker"])
        quote = quote_by_ticker[ticker]
        facts = book.fundamentals(ticker)
        technicals = book.technicals(ticker)
        filed = facts.source != "unavailable"
        basis = abs(row["cost_basis"])
        pnl_percent = (row["unrealized_pnl"] / basis * Decimal("100")) if basis else Decimal("0")
        rendered_positions.append(
            {
                "ticker": ticker,
                "name": quote.name,
                "quantity": format(row["quantity"], "f"),
                "averageCost": money(row["average_cost"]),
                "price": money(row["price"]),
                "marketValue": money(value),
                "weightPercent": money((value / equity * Decimal("100")) if equity else Decimal("0")),
                "unrealizedPnl": money(row["unrealized_pnl"]),
                "unrealizedPnlPercent": money(pnl_percent),
                "dailyPnl": money(row["daily_pnl"]),
                "realizedPnl": money(row["realized_pnl"]),
                "sector": row["sector"],
                "eps": None if not filed or not facts.eps else format(facts.eps, "f"),
                "support": _level(technicals.support),
                "resistance": _level(technicals.resistance),
                "rsi": None if technicals.rsi is None else f"{technicals.rsi:.2f}",
                "sma20": _level(technicals.sma20),
                "sma50": _level(technicals.sma50),
                "atr": _level(technicals.atr),
                "volume": technicals.volume,
                "relativeVolume": None if technicals.relative_volume is None else f"{technicals.relative_volume:.2f}",
                "rating": holding_rating(
                    price=float(row["price"]),
                    sma20=technicals.sma20,
                    sma50=technicals.sma50,
                    rsi=technicals.rsi,
                    eps_growth=facts.eps_growth if filed else None,
                    revenue_growth=facts.revenue_growth if filed else None,
                    pe=facts.pe if filed else None,
                ),
            }
        )
    return {
        "id": str(portfolio.id),
        "name": portfolio.name,
        "cash": money(portfolio.cash),
        "marketValue": money(market_value),
        "equity": money(equity),
        "buyingPower": money(portfolio.cash),
        "dailyPnl": money(daily),
        "dailyReturnPercent": money(day_return),
        "unrealizedPnl": money(unrealized),
        "realizedPnl": money(realized),
        "totalReturnPercent": money(total_return),
        "requiredReturnPercent": money(required_return(preference.capital, preference.daily_profit_target)),
        "positions": rendered_positions,
        "sectors": [{"sector": name, "weightPercent": money(value)} for name, value in sorted(sector_pcts.items())],
        "transactions": [_transaction(item) for item in reversed(ordered)],
        "equityCurve": [{"date": day.isoformat(), "equity": money(value)} for day, value in curve[-180:]],
        "performance": {
            "winRate": None if win_rate(trade_pnls) is None else round(win_rate(trade_pnls), 4),
            "profitFactor": _finite(profit_factor(trade_pnls)),
            "expectancy": None if expectancy(trade_pnls) is None else money(expectancy(trade_pnls)),
            "maxDrawdown": _drawdown_percent(curve),
            "sharpe": _finite(sharpe(returns)),
            "sortino": _finite(sortino(returns)),
            "closedTrades": len(trade_pnls),
            "note": "Sharpe and Sortino use the paper equity curve and a zero risk-free rate. They are not a forecast.",
        },
        "risk": {
            "openPositions": open_count,
            "maxOpenPositions": preference.max_open_positions,
            "largestPositionPercent": money(largest_pct),
            "maxPositionPercent": money(preference.max_position_pct),
            "largestSector": hottest,
            "largestSectorPercent": None if hottest is None else money(sector_pcts[hottest]),
            "maxSectorPercent": money(preference.max_sector_pct),
            "dailyLoss": money(loss_today),
            "maxDailyLoss": money(preference.max_daily_loss),
            "dailyLossStatus": daily_loss_status(loss_today, preference.max_daily_loss),
            "portfolioBeta": money(sum(betas, Decimal("0"))),
            "betaNote": "Beta weights use the reference betas stored with the universe, not a live regression.",
            "correlations": correlations,
            "breaches": _breaches(open_count, largest_pct, hottest, sector_pcts, preference, loss_today),
        },
    }


def plan_holding_change(
    portfolio: Portfolio,
    ticker: str,
    quantity: Decimal,
    price: Decimal,
) -> tuple[Decimal, list[dict[str, Decimal | str]]]:
    """Replace an open long with a new share count and buy price.

    A quantity of zero removes the holding. Cash moves by the difference in cost basis.
    The closing fill uses the current average cost, so the edit itself does not book a trading gain.
    """
    symbol = ticker.upper()
    fills = [_fill(item) for item in sorted(portfolio.transactions, key=lambda item: item.executed_at)]
    position = apply_fills(fills).get(symbol)
    if position is None or position.quantity == 0:
        raise ValueError(f"{symbol} is not an open holding.")
    if position.quantity < 0:
        raise ValueError(f"{symbol} is short. Close it from the trading desk.")
    if quantity < 0:
        raise ValueError("Shares cannot be negative.")
    if quantity > 0 and price <= 0:
        raise ValueError("Buy price must be positive.")
    removing = quantity == 0
    orders: list[dict[str, Decimal | str]] = [
        {
            "side": "sell",
            "quantity": position.quantity,
            "price": position.average_cost,
            "notes": "Removed holding." if removing else "Replaced holding before the edit.",
        }
    ]
    delta = cash_delta("sell", position.quantity, position.average_cost, Decimal("0"))
    if not removing:
        orders.append({"side": "buy", "quantity": quantity, "price": price, "notes": "Updated cost basis."})
        delta += cash_delta("buy", quantity, price, Decimal("0"))
    if portfolio.cash + delta < 0:
        raise ValueError("This change would make cash negative. Add cash first.")
    planned = list(fills)
    for order in orders:
        planned.append(Fill(symbol, str(order["side"]), Decimal(order["quantity"]), Decimal(order["price"])))
    apply_fills(planned)
    return delta, orders


def propose_trade(
    portfolio: Portfolio,
    book,
    ticker: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    fees: Decimal,
) -> None:
    fills = [_fill(item) for item in sorted(portfolio.transactions, key=lambda item: item.executed_at)]
    fills.append(Fill(ticker=ticker, side=side, quantity=quantity, price=price, fees=fees))
    apply_fills(fills)
    delta = cash_delta(side, quantity, price, fees)
    if portfolio.cash + delta < 0:
        raise ValueError("This order would make cash negative.")


def size_plan(account: Decimal, risk_percent: Decimal, entry: Decimal, stop: Decimal, target: Decimal | None) -> dict:
    plan = plan_position(account=account, risk_percent=risk_percent, entry=entry, stop=stop, target=target)
    return {
        "account": money(plan.account),
        "riskPercent": money(plan.risk_percent),
        "maxRisk": money(plan.max_risk),
        "entry": money(plan.entry),
        "stop": money(plan.stop),
        "target": None if plan.target is None else money(plan.target),
        "riskPerShare": money(plan.risk_per_share),
        "shares": format(plan.shares, "f"),
        "positionValue": money(plan.position_value),
        "riskReward": None if plan.risk_reward is None else money(plan.risk_reward),
        "note": (
            "Share count is the whole number that keeps the loss at the stop inside the stated risk. "
            "It is not a recommendation."
        ),
    }


def percent_target(basis: Decimal, percent: Decimal, direction: str) -> Decimal:
    if percent <= 0 or percent > 90:
        raise ValueError("Percent must be greater than 0 and at most 90.")
    if direction not in {"above", "below"}:
        raise ValueError("Direction must be above or below.")
    if basis <= 0:
        raise ValueError("Basis price must be positive.")
    sign = Decimal("1") if direction == "above" else Decimal("-1")
    return (basis * (Decimal("1") + sign * percent / Decimal("100"))).quantize(MONEY)


def price_crossed(price: Decimal, level: Decimal, direction: str) -> bool:
    if direction == "below":
        return price <= level
    return price >= level


def evaluate_alerts(
    alerts: list[Alert],
    book,
    notify: Callable[..., bool] | None = None,
) -> dict:
    triggered: dict = {}
    now = datetime.now(UTC)
    for alert in alerts:
        if not alert.enabled or not alert.ticker:
            triggered[alert.id] = False
            continue
        try:
            quote = book.quote(alert.ticker)
            technicals = book.technicals(alert.ticker)
        except KeyError:
            triggered[alert.id] = False
            continue
        hit = _alert_hit(alert, quote, technicals)
        triggered[alert.id] = hit
        if hit:
            alert.last_triggered_at = now
            wants_email = bool((alert.params or {}).get("email", True))
            if wants_email and not alert.notified and notify is not None and notify(alert, quote):
                alert.notified = True
        else:
            alert.notified = False
    return triggered


def _alert_hit(alert: Alert, quote, technicals) -> bool:
    params = alert.params or {}
    kind = alert.alert_type
    direction = str(params.get("direction", "above"))
    if kind == "price":
        return price_crossed(quote.price, Decimal(str(params.get("price", 0))), direction)
    if kind == "percent":
        target = params.get("target")
        if target in (None, ""):
            return False
        return price_crossed(quote.price, Decimal(str(target)), direction)
    if kind == "rsi":
        if technicals.rsi is None:
            return False
        level = float(params.get("level", 70))
        if params.get("direction") == "below":
            return technicals.rsi <= level
        return technicals.rsi >= level
    if kind == "volume":
        level = float(params.get("relativeVolume", 1.5))
        return technicals.relative_volume is not None and technicals.relative_volume >= level
    return False


def _correlations(positions, closes, book) -> list[dict[str, str | float]]:
    index_bars = []
    catalog_index = getattr(book, "_index", {})
    live_index = getattr(book, "_indexes", {})
    if "SPX" in catalog_index:
        index_bars = catalog_index["SPX"]
    elif "SPX" in live_index:
        index_bars = live_index["SPX"][1]
    index_returns = _returns(index_bars)
    rows = []
    tickers = [str(row["ticker"]) for row in positions]
    series = {ticker: _returns_from_closes(closes[ticker]) for ticker in tickers if ticker in closes}
    for ticker, values in series.items():
        score = pearson(values, index_returns)
        if score is not None:
            rows.append({"left": ticker, "right": "SPX", "value": round(score, 2)})
    for index, left in enumerate(tickers):
        for right in tickers[index + 1 :]:
            score = pearson(series.get(left, []), series.get(right, []))
            if score is not None:
                rows.append({"left": left, "right": right, "value": round(score, 2)})
    return rows[:12]


def _returns(bars) -> list[float]:
    values = []
    for previous, current in zip(bars, bars[1:], strict=False):
        if previous.close:
            values.append(float(current.close / previous.close - 1))
    return values[-60:]


def _returns_from_closes(series: dict) -> list[float]:
    ordered = [series[day] for day in sorted(series)]
    values = []
    for previous, current in zip(ordered, ordered[1:], strict=False):
        if previous:
            values.append(float(current / previous - 1))
    return values[-60:]


def _breaches(open_count, largest_pct, hottest, sector_pcts, preference, loss_today) -> list[str]:
    notes = []
    if open_count > preference.max_open_positions:
        notes.append("Open positions exceed the configured maximum.")
    if largest_pct > preference.max_position_pct:
        notes.append("One position is above the maximum position weight.")
    if hottest and sector_pcts[hottest] > preference.max_sector_pct:
        notes.append("One sector is above the maximum sector weight.")
    if loss_today >= preference.max_daily_loss:
        notes.append("Today's paper loss has reached the daily loss limit.")
    if not notes:
        notes.append("No configured risk limit is currently breached.")
    return notes


def _fill(item) -> Fill:
    return Fill(
        ticker=item.ticker,
        side=item.side,
        quantity=item.quantity,
        price=item.price,
        fees=item.fees,
    )


def _preference(preference) -> dict[str, object]:
    return {
        "capital": money(preference.capital),
        "dailyProfitTarget": money(preference.daily_profit_target),
        "tradingStyle": preference.trading_style,
        "riskTolerance": preference.risk_tolerance,
        "sectors": preference.sectors,
        "experience": preference.experience,
        "goals": preference.goals,
        "onboardingCompleted": preference.onboarding_completed,
        "maxPositionPct": money(preference.max_position_pct),
        "maxSectorPct": money(preference.max_sector_pct),
        "maxRiskPerTradePct": money(preference.max_risk_per_trade_pct),
        "maxDailyLoss": money(preference.max_daily_loss),
        "maxOpenPositions": preference.max_open_positions,
    }


def _watchlist(watchlist: Watchlist, quotes: dict[str, dict], book) -> dict:
    items = []
    for item in watchlist.items:
        quote = quotes.get(item.ticker)
        if quote is None:
            try:
                quote = book.quote(item.ticker).model_dump(mode="json", by_alias=True)
            except KeyError:
                quote = {}
        items.append(
            {
                "ticker": item.ticker,
                "notes": item.notes,
                "priority": item.priority,
                "targetPrice": None if item.target_price is None else money(item.target_price),
                "price": quote.get("price"),
                "changePercent": quote.get("changePercent"),
            }
        )
    return {
        "id": str(watchlist.id),
        "name": watchlist.name,
        "description": watchlist.description,
        "items": items,
    }


def _alert(alert: Alert, triggered: bool, book) -> dict:
    price = None
    change = None
    if alert.ticker:
        try:
            quote = book.quote(alert.ticker)
        except KeyError:
            quote = None
        if quote is not None:
            price = money(quote.price)
            change = format(quote.change_percent.quantize(MONEY), "f")
    params = alert.params or {}
    return {
        "id": str(alert.id),
        "ticker": alert.ticker,
        "alertType": alert.alert_type,
        "params": params,
        "price": price,
        "changePercent": change,
        "email": bool(params.get("email", True)),
        "notified": bool(alert.notified),
        "enabled": alert.enabled,
        "triggered": triggered,
        "lastTriggeredAt": None if alert.last_triggered_at is None else alert.last_triggered_at.isoformat(),
    }


def _journal(entry: JournalEntry) -> dict:
    return {
        "id": str(entry.id),
        "ticker": entry.ticker,
        "entryThesis": entry.entry_thesis,
        "exitThesis": entry.exit_thesis,
        "strategy": entry.strategy,
        "marketConditions": entry.market_conditions,
        "emotion": entry.emotion,
        "notes": entry.notes,
        "screenshotPath": entry.screenshot_path,
        "aiReview": entry.ai_review,
        "openedAt": None if entry.opened_at is None else entry.opened_at.isoformat(),
        "closedAt": None if entry.closed_at is None else entry.closed_at.isoformat(),
    }


def _saved(idea: SavedIdea) -> dict:
    return {
        "id": str(idea.id),
        "ticker": idea.ticker,
        "title": idea.title,
        "payload": idea.payload,
        "createdAt": idea.created_at.isoformat(),
    }


def _transaction(item) -> dict:
    return {
        "id": str(item.id),
        "ticker": item.ticker,
        "side": item.side,
        "quantity": format(item.quantity, "f"),
        "price": money(item.price),
        "fees": money(item.fees),
        "executedAt": item.executed_at.isoformat(),
        "notes": item.notes,
        "strategy": item.strategy,
    }


def _weight_fractions(raw: dict) -> dict[str, float]:
    mapping = {
        "technicalMomentum": "technical_momentum",
        "fundamentalStrength": "fundamental_strength",
        "analystSentiment": "analyst_sentiment",
        "earningsMomentum": "earnings_momentum",
        "valuation": "valuation",
        "sectorMomentum": "sector_momentum",
        "riskVolatility": "risk_volatility",
    }
    if "technical_momentum" in raw:
        return {key: float(raw[key]) for key in mapping.values()}
    return {snake: float(raw[camel]) for camel, snake in mapping.items()}


def _optional_int(value) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _optional_float(value) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _drawdown_percent(curve: list[tuple]) -> str | None:
    worst = max_drawdown([value for _day, value in curve])
    if worst is None:
        return None
    return money(worst * Decimal("100"))


def _finite(value: float | None) -> float | None:
    if value is None or value == float("inf"):
        return None
    return round(value, 4)
