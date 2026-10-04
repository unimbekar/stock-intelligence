from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from meridian_db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    preference: Mapped[UserPreference | None] = relationship(back_populates="user")
    portfolios: Mapped[list[Portfolio]] = relationship(back_populates="user")
    watchlists: Mapped[list[Watchlist]] = relationship(back_populates="user")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    capital: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    daily_profit_target: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    trading_style: Mapped[str] = mapped_column(String(32))
    risk_tolerance: Mapped[str] = mapped_column(String(32))
    sectors: Mapped[list] = mapped_column(JSONB, default=list)
    experience: Mapped[str] = mapped_column(String(32))
    goals: Mapped[str] = mapped_column(Text, default="")
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    theme: Mapped[str] = mapped_column(String(16), default="dark")
    max_position_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("20"))
    max_sector_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("40"))
    max_risk_per_trade_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("1"))
    max_daily_loss: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("1000"))
    max_open_positions: Mapped[int] = mapped_column(default=8)
    notify_email: Mapped[str] = mapped_column(String(255), default="", server_default="")

    user: Mapped[User] = relationship(back_populates="preference")


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    base_currency: Mapped[str] = mapped_column(String(8), default="USD")
    cash: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="portfolios")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="portfolio")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_portfolio_executed", "portfolio_id", "executed_at"),
        Index("ix_transactions_portfolio_ticker", "portfolio_id", "ticker"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE")
    )
    ticker: Mapped[str] = mapped_column(String(16))
    side: Mapped[str] = mapped_column(String(16))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    fees: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"))
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str] = mapped_column(Text, default="")
    strategy: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    portfolio: Mapped[Portfolio] = relationship(back_populates="transactions")


class Watchlist(Base):
    __tablename__ = "watchlists"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_watchlists_user_name"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="watchlists")
    items: Mapped[list[WatchlistItem]] = relationship(back_populates="watchlist", order_by="WatchlistItem.sort_order")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("watchlist_id", "ticker", name="uq_watchlist_ticker"),
        Index("ix_watchlist_items_order", "watchlist_id", "sort_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("watchlists.id", ondelete="CASCADE")
    )
    ticker: Mapped[str] = mapped_column(String(16))
    notes: Mapped[str] = mapped_column(Text, default="")
    target_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    priority: Mapped[str] = mapped_column(String(16), default="medium")
    sort_order: Mapped[int] = mapped_column(default=0)

    watchlist: Mapped[Watchlist] = relationship(back_populates="items")


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (Index("ix_alerts_user_enabled", "user_id", "enabled"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    ticker: Mapped[str | None] = mapped_column(String(16), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(32))
    params: Mapped[dict] = mapped_column(JSONB, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="SET NULL"), nullable=True
    )
    ticker: Mapped[str] = mapped_column(String(16))
    entry_thesis: Mapped[str] = mapped_column(Text, default="")
    exit_thesis: Mapped[str] = mapped_column(Text, default="")
    strategy: Mapped[str] = mapped_column(String(64), default="")
    market_conditions: Mapped[str] = mapped_column(Text, default="")
    emotion: Mapped[str] = mapped_column(String(32), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    screenshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ai_review: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SavedIdea(Base):
    __tablename__ = "saved_ideas"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    ticker: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(200))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScoringProfile(Base):
    __tablename__ = "scoring_profiles"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    weights: Mapped[dict] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_created", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    resource: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(64), default="")
    detail: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
