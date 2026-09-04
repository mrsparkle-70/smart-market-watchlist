"""Optional portfolio view: position math only, never brokerage execution."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Holding, MarketSnapshot, User
from app.schemas import HoldingUpsert

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


def _out(row: Holding, db: Session) -> dict:
    snapshot = db.execute(
        select(MarketSnapshot)
        .where(MarketSnapshot.symbol == row.symbol)
        .order_by(MarketSnapshot.captured_at.desc()).limit(1)
    ).scalar_one_or_none()
    current = snapshot.price if snapshot else None
    invested = row.quantity * row.average_cost
    value = row.quantity * current if current is not None else None
    return {
        "id": row.id, "symbol": row.symbol, "quantity": row.quantity, "average_cost": row.average_cost,
        "current_price": current, "invested_value": invested, "market_value": value,
        "unrealized_gain": value - invested if value is not None else None,
        "updated_at": row.updated_at, "data_quality": snapshot.data_quality if snapshot else "unavailable",
    }


@router.get("")
def list_holdings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Holding).where(Holding.user_id == user.id).order_by(Holding.symbol)).scalars()
    items = [_out(row, db) for row in rows]
    invested = sum(item["invested_value"] for item in items)
    market_value = sum(item["market_value"] or 0 for item in items)
    return {"items": items, "invested_value": invested, "market_value": market_value,
            "unrealized_gain": market_value - invested, "priced_items": sum(item["market_value"] is not None for item in items)}


@router.put("/{symbol}")
def upsert_holding(symbol: str, body: HoldingUpsert, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    normalized = symbol.strip().upper()
    if normalized != body.symbol.strip().upper():
        raise HTTPException(status_code=422, detail="Path symbol and body symbol must match")
    row = db.execute(select(Holding).where(Holding.user_id == user.id, Holding.symbol == normalized)).scalar_one_or_none()
    if row is None:
        row = Holding(user_id=user.id, symbol=normalized, quantity=body.quantity, average_cost=body.average_cost)
        db.add(row)
    else:
        row.quantity = body.quantity
        row.average_cost = body.average_cost
    db.commit()
    db.refresh(row)
    return _out(row, db)


@router.delete("/{symbol}", status_code=204)
def delete_holding(symbol: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.execute(select(Holding).where(Holding.user_id == user.id, Holding.symbol == symbol.upper())).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Holding not found")
    db.delete(row)
    db.commit()
