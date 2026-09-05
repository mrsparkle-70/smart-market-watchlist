"""Notification channels + delivery log (feature #1)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models import NotificationChannel, NotificationLog, User, UserPreferences
from app.services import notify as N

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class ChannelOut(BaseModel):
    id: int
    kind: str
    target: str
    enabled: bool
    verified: bool
    last_used_at: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class AddEmailChannel(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class AddWebPushChannel(BaseModel):
    endpoint: str = Field(min_length=10, max_length=1000)
    keys: dict


class ToggleChannel(BaseModel):
    enabled: bool


class LogOut(BaseModel):
    id: int
    kind: str
    title: str
    body: str
    status: str
    error: str
    created_at: str
    sent_at: Optional[str] = None
    read_at: Optional[str] = None

    class Config:
        from_attributes = True


class PreferencesOut(BaseModel):
    notification_enabled: bool
    daily_digest: bool
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    timezone: str


class PreferencesUpdate(BaseModel):
    notification_enabled: Optional[bool] = None
    daily_digest: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    timezone: Optional[str] = None


def _channel_to_dict(c: NotificationChannel) -> dict:
    return {
        "id": c.id, "kind": c.kind, "target": c.target,
        "enabled": c.enabled, "verified": c.verified,
        "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
        "created_at": c.created_at.isoformat(),
    }


def _log_to_dict(l: NotificationLog) -> dict:
    return {
        "id": l.id, "kind": l.kind, "title": l.title, "body": l.body,
        "status": l.status, "error": l.error,
        "created_at": l.created_at.isoformat(),
        "sent_at": l.sent_at.isoformat() if l.sent_at else None,
        "read_at": l.read_at.isoformat() if l.read_at else None,
    }


def _parse_hhmm(value: Optional[str]):
    from datetime import time
    if value is None or value == "":
        return None
    parts = value.split(":")
    if len(parts) != 2:
        raise HTTPException(status_code=422, detail="expected HH:MM")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise HTTPException(status_code=422, detail="invalid HH:MM")
    return time(hour=h, minute=m)


@router.get("/channels")
def list_my_channels(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_channel_to_dict(c) for c in N.list_channels(db, user.id)]


@router.post("/channels/email", status_code=201)
def add_email_channel(body: AddEmailChannel, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(status_code=422, detail="invalid email")
    ch = N.add_channel(db, user, "email", email)
    ch.verified = False
    db.commit()
    db.refresh(ch)
    return _channel_to_dict(ch)


@router.post("/channels/webpush", status_code=201)
def add_webpush_channel(body: AddWebPushChannel, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    keys = body.keys or {}
    if "p256dh" not in keys or "auth" not in keys:
        raise HTTPException(status_code=422, detail="keys must include p256dh and auth")
    ch = N.add_channel(db, user, "webpush", body.endpoint, subscription_keys=keys)
    return _channel_to_dict(ch)


@router.delete("/channels/{channel_id}", status_code=204)
def remove_my_channel(channel_id: int, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    ok = N.remove_channel(db, user.id, channel_id)
    if not ok:
        raise HTTPException(status_code=404, detail="channel not found")


@router.patch("/channels/{channel_id}")
def toggle_my_channel(channel_id: int, body: ToggleChannel,
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ch = N.set_channel_enabled(db, user.id, channel_id, body.enabled)
    if ch is None:
        raise HTTPException(status_code=404, detail="channel not found")
    return _channel_to_dict(ch)


@router.post("/channels/{channel_id}/test", status_code=202)
async def send_test(channel_id: int, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """Send a one-off "this is a test" through the chosen channel."""
    ch = db.get(NotificationChannel, channel_id)
    if ch is None or ch.user_id != user.id:
        raise HTTPException(status_code=404, detail="channel not found")
    if ch.kind == "email" and not settings.SMTP_HOST:
        raise HTTPException(status_code=409, detail="SMTP is not configured on the server")
    if ch.kind == "webpush" and not (settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY):
        raise HTTPException(status_code=409, detail="VAPID keys are not configured on the server")
    log = NotificationLog(
        user_id=user.id, channel_id=ch.id, kind=ch.kind,
        title="Test alert from Smart Market Watchlist",
        body="If you can read this, notifications are wired up correctly.",
        status="queued",
        payload_json={"test": True},
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    from app.core.database import SessionLocal
    delivered = await N.deliver_pending(SessionLocal)
    return {"queued_log_id": log.id, "delivered_in_this_call": delivered}


@router.get("/vapid-public-key")
def vapid_public_key(user: User = Depends(get_current_user)):
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=503, detail="VAPID not configured")
    return {"publicKey": settings.VAPID_PUBLIC_KEY}


@router.get("/log")
def list_log(limit: int = 50, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    limit = max(1, min(limit, 200))
    rows = list(db.execute(
        select(NotificationLog).where(NotificationLog.user_id == user.id)
        .order_by(NotificationLog.created_at.desc()).limit(limit)
    ).scalars())
    return [_log_to_dict(r) for r in rows]


@router.post("/log/{log_id}/read", status_code=204)
def mark_read(log_id: int, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    log = db.get(NotificationLog, log_id)
    if log is None or log.user_id != user.id:
        raise HTTPException(status_code=404, detail="log not found")
    from datetime import datetime, timezone
    log.read_at = datetime.now(timezone.utc)
    db.commit()


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    prefs = db.get(UserPreferences, user.id)
    if prefs is None:
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return PreferencesOut(
        notification_enabled=prefs.notification_enabled,
        daily_digest=prefs.daily_digest,
        quiet_hours_start=prefs.quiet_hours_start.isoformat() if prefs.quiet_hours_start else None,
        quiet_hours_end=prefs.quiet_hours_end.isoformat() if prefs.quiet_hours_end else None,
        timezone=prefs.timezone,
    )


@router.patch("/preferences")
def update_preferences(body: PreferencesUpdate, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    prefs = db.get(UserPreferences, user.id)
    if prefs is None:
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)
    data = body.model_dump(exclude_none=True)
    if "quiet_hours_start" in data:
        prefs.quiet_hours_start = _parse_hhmm(data.pop("quiet_hours_start"))
    if "quiet_hours_end" in data:
        prefs.quiet_hours_end = _parse_hhmm(data.pop("quiet_hours_end"))
    for k, v in data.items():
        setattr(prefs, k, v)
    db.commit()
    db.refresh(prefs)
    return {
        "notification_enabled": prefs.notification_enabled,
        "daily_digest": prefs.daily_digest,
        "quiet_hours_start": prefs.quiet_hours_start.isoformat() if prefs.quiet_hours_start else None,
        "quiet_hours_end": prefs.quiet_hours_end.isoformat() if prefs.quiet_hours_end else None,
        "timezone": prefs.timezone,
    }


