"""Create the local demo account. Safe to run more than once."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from meridian_config.product import load_product
from meridian_config.settings import get_settings
from meridian_db.models import (
    Alert,
    AuditLog,
    JournalEntry,
    Portfolio,
    ScoringProfile,
    Transaction,
    User,
    UserPreference,
    Watchlist,
    WatchlistItem,
)
from meridian_db.session import session_scope
from sqlalchemy import select

from meridian_api.passwords import hash_password

DEMO_EMAIL = "demo@meridian.local"
DEMO_PASSWORD = "meridian-demo"


def seed() -> None:
    settings = get_settings()
    product = load_product()
    with session_scope(settings.database_url) as session:
        existing = session.scalar(select(User).where(User.email == DEMO_EMAIL))
        if existing is not None:
            return

        user = User(
            email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
            display_name="Demo Trader",
            role="admin",
        )
        session.add(user)
        session.flush()

        session.add(
            UserPreference(
                user_id=user.id,
                capital=Decimal("50000"),
                daily_profit_target=Decimal("2000"),
                trading_style="swing",
                risk_tolerance="moderate",
                sectors=["AI", "Semiconductors", "Technology"],
                experience="intermediate",
                goals=(
                    "Practice a repeatable paper-trading process. "
                    "The $2,000 daily figure is a stress test of the risk tools, not a forecast."
                ),
                onboarding_completed=True,
                theme="dark",
                max_position_pct=Decimal("20"),
                max_sector_pct=Decimal("40"),
                max_risk_per_trade_pct=Decimal("1"),
                max_daily_loss=Decimal("1000"),
                max_open_positions=8,
            )
        )
        portfolio = Portfolio(
            user_id=user.id,
            name="Primary",
            description="Paper portfolio opened with the demo account.",
            cash=Decimal("38800.00"),
            is_default=True,
        )
        session.add(portfolio)
        session.flush()

        fills = [
            ("NVDA", "buy", "20", "160.00", datetime(2026, 6, 2, 14, 35, tzinfo=UTC), "swing"),
            ("MSFT", "buy", "10", "410.00", datetime(2026, 6, 16, 15, 5, tzinfo=UTC), "long-term"),
            ("LLY", "buy", "5", "780.00", datetime(2026, 7, 8, 14, 50, tzinfo=UTC), "swing"),
        ]
        for ticker, side, quantity, price, when, strategy in fills:
            session.add(
                Transaction(
                    portfolio_id=portfolio.id,
                    ticker=ticker,
                    side=side,
                    quantity=Decimal(quantity),
                    price=Decimal(price),
                    fees=Decimal("0"),
                    executed_at=when,
                    notes="Seeded paper fill. Demo prices, not a live tape.",
                    strategy=strategy,
                )
            )

        lists = {
            "AI Stocks": ["NVDA", "AMD", "AVGO", "PLTR"],
            "Day Trading": ["TSLA", "NVDA"],
            "Long Term": ["MSFT", "AAPL", "COST", "JPM"],
            "Healthcare": ["LLY"],
            "Quantum": [],
        }
        for name, tickers in lists.items():
            watchlist = Watchlist(user_id=user.id, name=name, description="Demo list")
            session.add(watchlist)
            session.flush()
            for order, ticker in enumerate(tickers):
                session.add(
                    WatchlistItem(
                        watchlist_id=watchlist.id,
                        ticker=ticker,
                        notes="",
                        priority="medium",
                        sort_order=order,
                    )
                )

        session.add(
            Alert(
                user_id=user.id,
                ticker="NVDA",
                alert_type="price",
                params={"direction": "above", "price": 200},
                enabled=True,
            )
        )
        session.add(
            JournalEntry(
                user_id=user.id,
                portfolio_id=portfolio.id,
                ticker="NVDA",
                entry_thesis="Demo note: added a small paper position to exercise the ledger.",
                strategy="swing",
                market_conditions="Demo series only.",
                emotion="calm",
                notes="Not a record of a real trade.",
                opened_at=datetime(2026, 6, 2, 14, 35, tzinfo=UTC),
            )
        )
        session.add(
            ScoringProfile(
                name="Default",
                weights=product.scoring_weights.model_dump(by_alias=True),
                is_active=True,
            )
        )
        session.add(
            AuditLog(
                user_id=user.id,
                action="seed",
                resource="user",
                resource_id=str(user.id),
                detail={"email": DEMO_EMAIL},
            )
        )


if __name__ == "__main__":
    seed()
