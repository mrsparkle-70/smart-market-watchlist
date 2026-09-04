"""Watchlist service: CRUD + symbol management + validation (section 9).

SECURITY: every query is scoped to the authenticated user (section 16).
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Watchlist, WatchlistSymbol
from app.providers.base import MarketDataProvider


def get_owned_watchlist(db: Session, user_id: int, watchlist_id: int) -> Watchlist:
    wl = db.get(Watchlist, watchlist_id)
    if wl is None or wl.user_id != user_id:
        # Do not leak existence of other users' watchlists
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return wl


def list_watchlists(db: Session, user_id: int) -> list[Watchlist]:
    return list(db.execute(select(Watchlist).where(Watchlist.user_id == user_id)).scalars())


def create_watchlist(db: Session, user_id: int, name: str) -> Watchlist:
    wl = Watchlist(user_id=user_id, name=name)
    db.add(wl)
    db.commit()
    db.refresh(wl)
    return wl


def rename_watchlist(db: Session, user_id: int, watchlist_id: int, name: str) -> Watchlist:
    wl = get_owned_watchlist(db, user_id, watchlist_id)
    wl.name = name
    db.commit()
    db.refresh(wl)
    return wl


def delete_watchlist(db: Session, user_id: int, watchlist_id: int) -> None:
    wl = get_owned_watchlist(db, user_id, watchlist_id)
    if wl.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete the default watchlist")
    db.delete(wl)
    db.commit()


async def add_symbol(db: Session, provider: MarketDataProvider, user_id: int,
                     watchlist_id: int, symbol: str, priority_tag: str = "normal") -> WatchlistSymbol:
    wl = get_owned_watchlist(db, user_id, watchlist_id)
    symbol = symbol.strip().upper()
    if len(symbol) > 20:
        raise HTTPException(status_code=422, detail="Invalid symbol")
    # Validate the ticker against the provider before persisting
    try:
        matches = await provider.search_symbol(symbol)
        valid = any(m.symbol == symbol for m in matches)
    except Exception:
        valid = True  # provider outage must not block watchlist editing; ingest will surface errors
    if not valid:
        raise HTTPException(status_code=422, detail=f"Unknown ticker symbol: {symbol}")
    exists = db.execute(
        select(WatchlistSymbol).where(
            WatchlistSymbol.watchlist_id == wl.id, WatchlistSymbol.symbol == symbol
        )
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=409, detail=f"{symbol} is already in this watchlist")
    profile = None
    try:
        profile = await provider.get_company_profile(symbol)
    except Exception:
        pass
    ws = WatchlistSymbol(
        watchlist_id=wl.id, symbol=symbol,
        display_name=profile.name if profile else symbol,
        exchange=profile.exchange if profile else "",
        sort_order=len(wl.symbols), priority_tag=priority_tag,
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


def remove_symbol(db: Session, user_id: int, watchlist_id: int, symbol: str) -> None:
    wl = get_owned_watchlist(db, user_id, watchlist_id)
    ws = db.execute(
        select(WatchlistSymbol).where(
            WatchlistSymbol.watchlist_id == wl.id, WatchlistSymbol.symbol == symbol.upper()
        )
    ).scalar_one_or_none()
    if ws is None:
        raise HTTPException(status_code=404, detail="Symbol not found in watchlist")
    db.delete(ws)
    db.commit()


def update_priority(db: Session, user_id: int, watchlist_id: int, symbol: str, priority_tag: str) -> WatchlistSymbol:
    wl = get_owned_watchlist(db, user_id, watchlist_id)
    ws = db.execute(
        select(WatchlistSymbol).where(
            WatchlistSymbol.watchlist_id == wl.id, WatchlistSymbol.symbol == symbol.upper()
        )
    ).scalar_one_or_none()
    if ws is None:
        raise HTTPException(status_code=404, detail="Symbol not found in watchlist")
    ws.priority_tag = priority_tag
    db.commit()
    db.refresh(ws)
    return ws


def reorder_symbols(db: Session, user_id: int, watchlist_id: int, symbols: list[str]) -> None:
    wl = get_owned_watchlist(db, user_id, watchlist_id)
    for idx, sym in enumerate(symbols):
        ws = db.execute(
            select(WatchlistSymbol).where(
                WatchlistSymbol.watchlist_id == wl.id, WatchlistSymbol.symbol == sym.upper()
            )
        ).scalar_one_or_none()
        if ws:
            ws.sort_order = idx
    db.commit()
