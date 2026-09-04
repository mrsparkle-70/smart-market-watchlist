"""Provider abstraction. The app is never tied to one vendor (see docs/architecture.md)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class Quote:
    symbol: str
    price: float
    previous_close: float
    open_price: float | None = None
    high_price: float | None = None
    low_price: float | None = None
    volume: float | None = None
    currency: str = "USD"
    market_status: str = "unknown"  # open|closed|pre|after|unknown
    source_timestamp: datetime | None = None
    provider: str = ""


@dataclass
class Candle:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class CompanyProfile:
    symbol: str
    name: str
    exchange: str = ""
    sector: str = ""
    industry: str = ""


@dataclass
class CorporateEvent:
    symbol: str
    event_type: str  # earnings|dividend|split|guidance|analyst_rating|ma
    title: str
    effective_at: datetime
    details: dict = field(default_factory=dict)


@dataclass
class NewsArticle:
    symbol: str
    headline: str
    source: str
    url: str
    published_at: datetime
    sentiment_label: str = "neutral"


class MarketDataProvider(Protocol):
    """Every vendor integration must implement this interface."""

    name: str

    async def get_quote(self, symbol: str) -> Quote: ...
    async def get_ohlcv(self, symbol: str, interval: str = "1d", lookback_days: int = 120) -> list[Candle]: ...
    async def get_company_profile(self, symbol: str) -> CompanyProfile: ...
    async def get_corporate_events(self, symbol: str) -> list[CorporateEvent]: ...
    async def get_news(self, symbol: str, since: datetime | None = None) -> list[NewsArticle]: ...
    async def search_symbol(self, query: str) -> list[CompanyProfile]: ...
