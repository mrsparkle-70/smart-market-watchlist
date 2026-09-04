"""Market data routes (section 12). API keys stay server-side."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_market_provider
from app.core.database import get_db
from app.models import MarketEvent, MarketSnapshot, PriceAlert, SymbolNote, User, Watchlist, WatchlistSymbol
from app.providers.base import MarketDataProvider
from app.services.features import classify_freshness
from app.services.ingest import ingest_symbol, ingest_watchlist
from app.services.watchlist_service import get_owned_watchlist
from app.schemas import AlertCreate, SymbolNoteUpdate

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/search")
async def search_symbols(q: str, user: User = Depends(get_current_user),
                         provider: MarketDataProvider = Depends(get_market_provider)):
    query = q.strip()
    if len(query) < 2:
        return []
    try:
        matches = await provider.search_symbol(query)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Symbol search unavailable: {exc}") from exc
    return [{"symbol": p.symbol, "name": p.name, "exchange": p.exchange, "industry": p.industry} for p in matches]


def _ensure_watched(db: Session, user_id: int, symbol: str) -> str:
    normalized = symbol.upper()
    watched = db.execute(
        select(WatchlistSymbol.symbol).join(Watchlist, Watchlist.id == WatchlistSymbol.watchlist_id).where(
            Watchlist.user_id == user_id, WatchlistSymbol.symbol == normalized
        ).limit(1)
    ).scalar_one_or_none()
    if watched is None:
        raise HTTPException(status_code=404, detail="Symbol is not in one of your watchlists")
    return normalized


@router.get("/{symbol}/note")
def get_symbol_note(symbol: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    normalized = _ensure_watched(db, user.id, symbol)
    note = db.execute(select(SymbolNote).where(SymbolNote.user_id == user.id, SymbolNote.symbol == normalized)).scalar_one_or_none()
    return {"symbol": normalized, "body": note.body if note else "", "updated_at": note.updated_at if note else None}


@router.put("/{symbol}/note")
def save_symbol_note(symbol: str, body: SymbolNoteUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    normalized = _ensure_watched(db, user.id, symbol)
    text = body.body
    note = db.execute(select(SymbolNote).where(SymbolNote.user_id == user.id, SymbolNote.symbol == normalized)).scalar_one_or_none()
    if note is None:
        note = SymbolNote(user_id=user.id, symbol=normalized, body=text)
        db.add(note)
    else:
        note.body = text
    db.commit()
    db.refresh(note)
    return {"symbol": normalized, "body": note.body, "updated_at": note.updated_at}


@router.get("/{symbol}/alerts")
def list_alerts(symbol: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    normalized = _ensure_watched(db, user.id, symbol)
    rows = db.execute(select(PriceAlert).where(PriceAlert.user_id == user.id, PriceAlert.symbol == normalized).order_by(PriceAlert.created_at.desc())).scalars()
    return [{"id": a.id, "symbol": a.symbol, "condition": a.condition, "threshold": a.threshold,
             "enabled": a.enabled, "created_at": a.created_at, "last_triggered_at": a.last_triggered_at,
             "last_triggered_value": a.last_triggered_value} for a in rows]


@router.post("/{symbol}/alerts", status_code=201)
def create_alert(symbol: str, body: AlertCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    normalized = _ensure_watched(db, user.id, symbol)
    alert = PriceAlert(user_id=user.id, symbol=normalized, condition=body.condition, threshold=body.threshold)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return {"id": alert.id, "symbol": alert.symbol, "condition": alert.condition, "threshold": alert.threshold,
            "enabled": alert.enabled, "created_at": alert.created_at, "last_triggered_at": alert.last_triggered_at,
            "last_triggered_value": alert.last_triggered_value}


@router.delete("/{symbol}/alerts/{alert_id}", status_code=204)
def delete_alert(symbol: str, alert_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    normalized = _ensure_watched(db, user.id, symbol)
    alert = db.execute(select(PriceAlert).where(PriceAlert.id == alert_id, PriceAlert.user_id == user.id, PriceAlert.symbol == normalized)).scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.delete(alert)
    db.commit()


def _latest_snapshot(db: Session, symbol: str) -> MarketSnapshot:
    snap = db.execute(
        select(MarketSnapshot).where(MarketSnapshot.symbol == symbol.upper())
        .order_by(MarketSnapshot.captured_at.desc()).limit(1)
    ).scalar_one_or_none()
    if snap is None:
        raise HTTPException(status_code=404, detail=f"No data ingested yet for {symbol.upper()}")
    return snap


@router.get("/{symbol}/latest")
def latest(symbol: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    snap = _latest_snapshot(db, symbol)
    market_open = snap.market_status == "open"
    freshness = classify_freshness(snap.source_timestamp, datetime.now(timezone.utc), market_open)
    return {
        "symbol": snap.symbol,
        "price": snap.price,
        "previous_close": snap.previous_close,
        "open_price": snap.open_price,
        "high_price": snap.high_price,
        "low_price": snap.low_price,
        "volume": snap.volume,
        "market_status": snap.market_status,
        "change_since_close_pct": round((snap.price - snap.previous_close) / snap.previous_close * 100, 2)
        if snap.previous_close else None,
        "freshness": freshness,
        "data_quality": snap.data_quality,
        "source_timestamp": snap.source_timestamp,
        "captured_at": snap.captured_at,
        "provider": snap.provider,
    }


@router.get("/{symbol}/history")
def history(symbol: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    snaps = list(db.execute(
        select(MarketSnapshot).where(MarketSnapshot.symbol == symbol.upper())
        .order_by(MarketSnapshot.captured_at.asc()).limit(500)
    ).scalars())
    return [
        {"ts": s.captured_at, "open": s.open_price, "high": s.high_price,
         "low": s.low_price, "close": s.price, "volume": s.volume}
        for s in snaps
    ]


@router.get("/{symbol}/analytics")
def analytics(symbol: str, days: int = 90, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    normalized = symbol.upper()
    days = max(1, min(days, 730))
    snaps = list(db.execute(
        select(MarketSnapshot).where(MarketSnapshot.symbol == normalized)
        .order_by(MarketSnapshot.captured_at.asc()).limit(2000)
    ).scalars())
    if not snaps:
        return {"symbol": normalized, "observations": 0, "first_price": None, "last_price": None,
                "return_pct": None, "high": None, "low": None, "max_drawdown_pct": None,
                "positive_observations": 0, "negative_observations": 0, "window_days": days}
    selected = snaps[-days:]
    prices = [s.price for s in selected]
    first, last = prices[0], prices[-1]
    peak = prices[0]
    max_drawdown = 0.0
    for price in prices:
        peak = max(peak, price)
        if peak:
            max_drawdown = min(max_drawdown, (price - peak) / peak * 100.0)
    positive = sum(1 for before, after in zip(prices, prices[1:]) if after > before)
    negative = sum(1 for before, after in zip(prices, prices[1:]) if after < before)
    return {"symbol": normalized, "observations": len(selected), "first_price": first, "last_price": last,
            "return_pct": (last - first) / first * 100 if first else None, "high": max(prices), "low": min(prices),
            "max_drawdown_pct": max_drawdown, "positive_observations": positive,
            "negative_observations": negative, "window_days": days}


@router.get("/{symbol}/events")
def events(symbol: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = list(db.execute(
        select(MarketEvent).where(MarketEvent.symbol == symbol.upper())
        .order_by(MarketEvent.detected_at.desc()).limit(100)
    ).scalars())
    return [{
        "id": e.id, "event_type": e.event_type, "title": e.title, "summary": e.summary,
        "attention_score": e.attention_score, "confidence_score": e.confidence_score,
        "final_score": e.final_score, "severity": e.severity,
        "detected_at": e.detected_at, "evidence": e.evidence_json,
    } for e in rows]


@router.get("/{symbol}/news")
def news(symbol: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import NewsItem

    rows = list(db.execute(
        select(NewsItem).where(NewsItem.symbol == symbol.upper())
        .order_by(NewsItem.published_at.desc().nullslast()).limit(30)
    ).scalars())
    return [{
        "headline": n.headline, "source": n.source, "url": n.url,
        "published_at": n.published_at, "relevance_score": n.relevance_score,
        "sentiment_label": n.sentiment_label,
    } for n in rows]


@router.post("/{symbol}/refresh")
async def refresh(symbol: str, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_market_provider)):
    """Manual pipeline trigger for one symbol (used by the demo storyline)."""
    try:
        evt = await ingest_symbol(db, provider, symbol.upper())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Provider failure: {exc}")
    return {"symbol": symbol.upper(), "new_event": bool(evt),
            "event_score": evt.final_score if evt else None}


@router.post("/refresh-watchlist/{watchlist_id}")
async def refresh_watchlist(watchlist_id: int, user: User = Depends(get_current_user),
                            db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_market_provider)):
    get_owned_watchlist(db, user.id, watchlist_id)
    try:
        results = await ingest_watchlist(db, provider, watchlist_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Market data provider failure: {exc}") from exc
    return {"watchlist_id": watchlist_id, "results": results}
