"""SQLAlchemy models: users, watchlists, snapshots, features, events, news, preferences."""
from __future__ import annotations
from datetime import datetime, timezone

from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # "Since your last visit" anchor. Only updated AFTER a page load succeeds.
    last_visit_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    watchlists: Mapped[list["Watchlist"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    preferences: Mapped[Optional[UserPreferences]] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    event_states: Mapped[list["UserEventState"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="watchlists")
    symbols: Mapped[list["WatchlistSymbol"]] = relationship(
        back_populates="watchlist", cascade="all, delete-orphan", order_by="WatchlistSymbol.sort_order"
    )


class WatchlistSymbol(Base):
    __tablename__ = "watchlist_symbols"
    __table_args__ = (UniqueConstraint("watchlist_id", "symbol", name="uq_watchlist_symbol"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    watchlist_id: Mapped[int] = mapped_column(ForeignKey("watchlists.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    display_name: Mapped[str] = mapped_column(String(200), default="")
    exchange: Mapped[str] = mapped_column(String(50), default="")
    asset_type: Mapped[str] = mapped_column(String(30), default="stock")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # Personal relevance tuning for the scoring system
    priority_tag: Mapped[str] = mapped_column(String(30), default="normal")

    watchlist: Mapped[Watchlist] = relationship(back_populates="symbols")


class MarketSnapshot(Base):
    """Raw, normalized quote snapshot. Never overwritten by another provider silently."""
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    provider: Mapped[str] = mapped_column(String(50))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    price: Mapped[float] = mapped_column(Float)
    previous_close: Mapped[float] = mapped_column(Float)
    open_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    high_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    low_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    market_status: Mapped[str] = mapped_column(String(20), default="unknown")  # open|closed|pre|after|unknown
    source_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    data_quality: Mapped[str] = mapped_column(String(20), default="ok")  # ok|delayed|stale|unknown|conflicted
    is_delayed: Mapped[bool] = mapped_column(Boolean, default=False)


class MarketFeature(Base):
    """Derived per-snapshot analytics used by change detection and scoring."""
    __tablename__ = "market_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    return_1d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    return_since_previous_snapshot: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volatility_20d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volatility_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    relative_return: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ma_20: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ma_50: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ma_200: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gap_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class MarketEvent(Base):
    """A detected, scored, explained change. The heart of the attention feed."""
    __tablename__ = "market_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    attention_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0)
    final_score: Mapped[float] = mapped_column(Float, default=0.0)  # attention_score * confidence
    severity: Mapped[str] = mapped_column(String(20), default="notable")
    title: Mapped[str] = mapped_column(String(300), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    evidence_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="open")
    dedupe_key: Mapped[str] = mapped_column(String(255), default="", index=True)


class UserEventState(Base):
    """User-level state per event: seen / reviewed / dismissed / saved."""
    __tablename__ = "user_event_state"
    __table_args__ = (UniqueConstraint("user_id", "event_id", name="uq_user_event"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("market_events.id"), index=True)
    seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    saved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="event_states")
    event: Mapped[MarketEvent] = relationship()


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    source: Mapped[str] = mapped_column(String(120), default="")
    url: Mapped[str] = mapped_column(String(500), default="")
    headline: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    sentiment_label: Mapped[str] = mapped_column(String(20), default="neutral")
    raw_metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    price_threshold: Mapped[float] = mapped_column(Float, default=3.0)
    volume_threshold: Mapped[float] = mapped_column(Float, default=2.0)
    volatility_threshold: Mapped[float] = mapped_column(Float, default=1.5)
    preferred_sectors: Mapped[str] = mapped_column(String(300), default="")
    notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    timezone: Mapped[str] = mapped_column(String(60), default="UTC")

    user: Mapped[User] = relationship(back_populates="preferences")


class SymbolNote(Base):
    """Private user journal entry for a watched symbol."""
    __tablename__ = "symbol_notes"
    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_user_symbol_note"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    body: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class PriceAlert(Base):
    """Account-scoped alert evaluated on each successful quote refresh."""
    __tablename__ = "price_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    condition: Mapped[str] = mapped_column(String(30))  # price_above|price_below|move_up|move_down
    threshold: Mapped[float] = mapped_column(Float)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_triggered_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class Holding(Base):
    """A user's optional position record; never treated as a trade order."""
    __tablename__ = "holdings"
    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_user_holding_symbol"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    average_cost: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
