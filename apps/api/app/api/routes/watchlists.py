"""Watchlist + symbol routes (section 12). Every route verifies ownership."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_market_provider
from app.core.database import get_db
from app.models import User
from app.providers.base import MarketDataProvider
from app.schemas import (
    SymbolAdd,
    BulkSymbolAdd,
    SymbolReorder,
    SymbolPriorityUpdate,
    WatchlistCreate,
    WatchlistOut,
    WatchlistUpdate,
)
from app.services import watchlist_service as WLS

router = APIRouter(prefix="/api/watchlists", tags=["watchlists"])


@router.get("", response_model=list[WatchlistOut])
def list_watchlists(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return WLS.list_watchlists(db, user.id)


@router.post("", response_model=WatchlistOut, status_code=201)
def create_watchlist(body: WatchlistCreate, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    return WLS.create_watchlist(db, user.id, body.name)


@router.patch("/{watchlist_id}", response_model=WatchlistOut)
def rename_watchlist(watchlist_id: int, body: WatchlistUpdate,
                     user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return WLS.rename_watchlist(db, user.id, watchlist_id, body.name)


@router.delete("/{watchlist_id}", status_code=204)
def delete_watchlist(watchlist_id: int, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    WLS.delete_watchlist(db, user.id, watchlist_id)


@router.get("/{watchlist_id}/symbols")
def list_symbols(watchlist_id: int, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    wl = WLS.get_owned_watchlist(db, user.id, watchlist_id)
    return [
        {"symbol": s.symbol, "display_name": s.display_name, "exchange": s.exchange,
         "asset_type": s.asset_type, "sort_order": s.sort_order, "priority_tag": s.priority_tag}
        for s in wl.symbols
    ]


@router.post("/{watchlist_id}/symbols", status_code=201)
async def add_symbol(watchlist_id: int, body: SymbolAdd, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_market_provider)):
    ws = await WLS.add_symbol(db, provider, user.id, watchlist_id, body.symbol, body.priority_tag)
    return {"symbol": ws.symbol, "display_name": ws.display_name, "exchange": ws.exchange,
            "sort_order": ws.sort_order, "priority_tag": ws.priority_tag}


@router.post("/{watchlist_id}/symbols/bulk")
async def bulk_add_symbols(watchlist_id: int, body: BulkSymbolAdd, user: User = Depends(get_current_user),
                           db: Session = Depends(get_db), provider: MarketDataProvider = Depends(get_market_provider)):
    WLS.get_owned_watchlist(db, user.id, watchlist_id)
    normalized = list(dict.fromkeys(s.strip().upper() for raw in body.symbols for s in raw.replace(",", " ").split() if s.strip()))
    added, errors = [], []
    for symbol in normalized:
        try:
            row = await WLS.add_symbol(db, provider, user.id, watchlist_id, symbol, body.priority_tag)
            added.append(row.symbol)
        except HTTPException as exc:
            errors.append({"symbol": symbol, "error": str(exc.detail)})
    return {"added": added, "errors": errors}


@router.delete("/{watchlist_id}/symbols/{symbol}", status_code=204)
def remove_symbol(watchlist_id: int, symbol: str, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    WLS.remove_symbol(db, user.id, watchlist_id, symbol)


@router.patch("/{watchlist_id}/symbols/{symbol}/priority")
def update_priority(watchlist_id: int, symbol: str, body: SymbolPriorityUpdate,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = WLS.update_priority(db, user.id, watchlist_id, symbol, body.priority_tag)
    return {"symbol": row.symbol, "priority_tag": row.priority_tag}


@router.patch("/{watchlist_id}/symbols/reorder")
def reorder_symbols(watchlist_id: int, body: SymbolReorder, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    WLS.reorder_symbols(db, user.id, watchlist_id, body.symbols)
    return {"ok": True}
