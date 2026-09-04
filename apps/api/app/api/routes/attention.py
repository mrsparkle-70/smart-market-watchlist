"""Attention feed, event state, visit tracking, preferences, SSE stream (section 12)."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User, UserPreferences
from app.schemas import PreferencesUpdate
from app.services import feed_service as F

router = APIRouter(tags=["attention"])


class VisitResponse(BaseModel):
    previous_visit_at: Optional[datetime] = None
    recorded_visit_at: datetime


@router.get("/api/attention-feed")
def attention_feed(watchlist_id: Optional[int] = None, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    if watchlist_id is None:
        from app.services.watchlist_service import list_watchlists

        watchlists = list_watchlists(db, user.id)
        if not watchlists:
            return {"since": None, "generated_at": None, "cards": [], "summary": None,
                    "change_brief": "", "tags": {}}
        watchlist_id = watchlists[0].id
    return F.build_attention_feed(db, user, watchlist_id)


@router.post("/api/events/{event_id}/seen")
def mark_seen(event_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = F.set_event_state(db, user, event_id, "seen")
    return {"event_id": event_id, "seen_at": state.seen_at}


@router.post("/api/events/{event_id}/reviewed")
def mark_reviewed(event_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = F.set_event_state(db, user, event_id, "reviewed")
    return {"event_id": event_id, "reviewed_at": state.reviewed_at}


@router.post("/api/events/{event_id}/dismiss")
def mark_dismissed(event_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = F.set_event_state(db, user, event_id, "dismissed")
    return {"event_id": event_id, "dismissed_at": state.dismissed_at}


@router.post("/api/events/{event_id}/save")
def mark_saved(event_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    state = F.set_event_state(db, user, event_id, "saved")
    return {"event_id": event_id, "saved_at": state.saved_at}


@router.post("/api/sessions/visit", response_model=VisitResponse)
def record_visit(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Called AFTER the dashboard page loads successfully (section 7)."""
    previous = F.record_visit(db, user)
    return VisitResponse(previous_visit_at=previous, recorded_visit_at=datetime.now(timezone.utc))


@router.get("/api/preferences")
def get_preferences(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prefs = db.get(UserPreferences, user.id)
    if prefs is None:
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return {
        "price_threshold": prefs.price_threshold,
        "volume_threshold": prefs.volume_threshold,
        "volatility_threshold": prefs.volatility_threshold,
        "notification_enabled": prefs.notification_enabled,
        "timezone": prefs.timezone,
    }


@router.patch("/api/preferences")
def update_preferences(body: PreferencesUpdate, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    prefs = db.get(UserPreferences, user.id)
    if prefs is None:
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(prefs, field, value)
    db.commit()
    return {"ok": True}


@router.get("/api/stream/watchlist/{watchlist_id}")
async def stream_watchlist(watchlist_id: int, request: Request,
                           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Server-Sent Events for one-way live refresh (simpler than WebSockets)."""
    F.get_owned_watchlist(db, user.id, watchlist_id)  # authorization

    async def event_generator():
        heartbeat = 0
        while True:
            if await request.is_disconnected():
                break
            payload = json.dumps({"type": "heartbeat", "ts": heartbeat})
            yield f"data: {payload}\n\n"
            heartbeat += 1
            await asyncio.sleep(15)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
