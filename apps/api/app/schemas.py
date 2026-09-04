"""Pydantic request/response schemas (input validation at every boundary)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from typing import Optional

from pydantic import BaseModel, EmailStr, Field

# ---- Auth -----------------------------------------------------------------
from app.core.config import settings


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    last_visit_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- Watchlists -------------------------------------------------------------
class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class WatchlistUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class SymbolAdd(BaseModel):
    symbol: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9.\-]+$")
    priority_tag: Literal["normal", "high_priority", "long_term", "speculative", "ignore_short_term"] = "normal"


class BulkSymbolAdd(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=100)
    priority_tag: Literal["normal", "high_priority", "long_term", "speculative", "ignore_short_term"] = "normal"


class SymbolReorder(BaseModel):
    symbols: list[str]


class SymbolPriorityUpdate(BaseModel):
    priority_tag: Literal["normal", "high_priority", "long_term", "speculative", "ignore_short_term"]


class SymbolNoteUpdate(BaseModel):
    body: str = Field(default="", max_length=5000)


class AlertCreate(BaseModel):
    condition: Literal["price_above", "price_below", "move_up", "move_down"]
    threshold: float = Field(gt=0, le=1_000_000)


class HoldingUpsert(BaseModel):
    symbol: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9.\-]+$")
    quantity: float = Field(gt=0, le=100_000_000)
    average_cost: float = Field(gt=0, le=1_000_000)


class WatchlistSymbolOut(BaseModel):
    symbol: str
    display_name: str
    exchange: str
    asset_type: str
    sort_order: int
    priority_tag: str

    class Config:
        from_attributes = True


class WatchlistOut(BaseModel):
    id: int
    name: str
    is_default: bool
    symbols: list[WatchlistSymbolOut] = []

    class Config:
        from_attributes = True


# ---- Market data --------------------------------------------------------------
class QuoteOut(BaseModel):
    symbol: str
    price: float
    previous_close: float
    change_since_close_pct: float
    change_since_last_visit_pct: Optional[float] = None
    volume: Optional[float] = None
    market_status: str
    freshness: str
    source_timestamp: Optional[datetime] = None
    captured_at: datetime
    provider: str


class CandleOut(BaseModel):
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


# ---- Attention feed ------------------------------------------------------------
class EventEvidence(BaseModel):
    """Explainability mode: trigger, baseline, current value, window, source, confidence."""
    trigger: str
    baseline: str
    current: str
    window: str
    source: str
    confidence: float
    extra: dict[str, Any] = {}


class AttentionCard(BaseModel):
    id: int
    symbol: str
    company_name: str
    event_type: str
    title: str
    summary: str
    attention_score: float
    confidence_score: float
    final_score: float
    severity: str
    detected_at: datetime
    price: Optional[float] = None
    change_since_last_visit_pct: Optional[float] = None
    change_since_close_pct: Optional[float] = None
    freshness: str = "unknown"
    evidence: Optional[EventEvidence] = None
    user_state: dict[str, Optional[datetime]] = {}


class WatchlistSummary(BaseModel):
    total_symbols: int
    meaningful_changes: int
    stale_instruments: int
    biggest_positive_move: Optional[dict[str, Any]] = None
    biggest_negative_move: Optional[dict[str, Any]] = None


class AttentionFeedOut(BaseModel):
    since: Optional[datetime]
    generated_at: datetime
    cards: list[AttentionCard]
    summary: WatchlistSummary
    change_brief: str


class EventStateUpdate(BaseModel):
    pass


# ---- Preferences ------------------------------------------------------------
class PreferencesUpdate(BaseModel):
    price_threshold: Optional[float] = Field(default=None, ge=0.1, le=50)
    volume_threshold: Optional[float] = Field(default=None, ge=1.0, le=20)
    volatility_threshold: Optional[float] = Field(default=None, ge=1.0, le=10)
    notification_enabled: Optional[bool] = None
    timezone: Optional[str] = None
