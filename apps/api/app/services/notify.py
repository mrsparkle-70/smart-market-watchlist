"""Notification delivery (feature #1).

Sends triggered price alerts out of the in-process pipeline through one or
more user-subscribed channels: email (SMTP) and web push (VAPID). Every
attempt is recorded in `notification_logs` so users have an in-app feed
even when external delivery fails or is unconfigured.

Design choices
--------------
* Optional infrastructure. SMTP and VAPID are not required to run the app.
  If unconfigured, sends are recorded as `queued` and otherwise no-op.
* Pluggable senders. New channels (Slack, Discord, SMS) slot in by adding
  a class that implements `send()` and registering it in `SENDERS`.
* Quiet hours / daily digest are honored at enqueue time: a trigger during
  quiet hours becomes a single digest message instead of an immediate send.
"""
from __future__ import annotations

import asyncio
import json
import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime, time, timezone
from email.message import EmailMessage
from typing import Callable, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    NotificationChannel,
    NotificationLog,
    PriceAlert,
    User,
    UserPreferences,
)

logger = logging.getLogger("smw.notify")


@dataclass
class AlertPayload:
    """Structured, channel-agnostic description of what fired."""
    alert_id: int
    symbol: str
    condition: str
    threshold: float
    triggered_value: float | None
    triggered_at: datetime
    company_name: str = ""

    @property
    def title(self) -> str:
        if self.condition == "price_above":
            return f"{self.symbol} is above ${self.threshold:,.2f}"
        if self.condition == "price_below":
            return f"{self.symbol} is below ${self.threshold:,.2f}"
        if self.condition == "move_up":
            return f"{self.symbol} is up {self.threshold:+.1f}% or more"
        if self.condition == "move_down":
            return f"{self.symbol} is down {self.threshold:+.1f}% or more"
        return f"{self.symbol} alert"

    @property
    def body(self) -> str:
        price_part = ""
        if self.triggered_value is not None:
            price_part = f" (last ${self.triggered_value:,.2f})"
        return f"{self.company_name or self.symbol}: {self.title}{price_part}."


class Sender(Protocol):
    """A delivery mechanism. Implementations must be safe to call concurrently."""
    name: str

    async def send(self, channel: NotificationChannel, subject: str, body: str) -> tuple[bool, str]:
        """Return (ok, error_message). `error_message` is empty on success."""
        ...


class EmailSender:
    name = "email"

    def __init__(self, host: str | None = None, port: int | None = None,
                 username: str | None = None, password: str | None = None,
                 from_addr: str | None = None, use_tls: bool | None = None) -> None:
        self.host = host or settings.SMTP_HOST
        self.port = port if port is not None else settings.SMTP_PORT
        self.username = username if username is not None else settings.SMTP_USERNAME
        self.password = password if password is not None else settings.SMTP_PASSWORD
        self.from_addr = from_addr or settings.SMTP_FROM
        self.use_tls = settings.SMTP_USE_TLS if use_tls is None else use_tls

    def is_configured(self) -> bool:
        return bool(self.host)

    async def send(self, channel: NotificationChannel, subject: str, body: str) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "SMTP not configured"
        # SMTP is blocking; run in a thread so the event loop stays free.
        return await asyncio.to_thread(self._send_sync, channel.target, subject, body)

    def _send_sync(self, to: str, subject: str, body: str) -> tuple[bool, str]:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = to
        msg.set_content(body)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=15) as s:
                if self.use_tls:
                    s.starttls()
                if self.username:
                    s.login(self.username, self.password)
                s.send_message(msg)
            return True, ""
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"


class WebPushSender:
    name = "webpush"

    def __init__(self, private_key: str | None = None, public_key: str | None = None,
                 subject: str | None = None) -> None:
        self.private_key = private_key or settings.VAPID_PRIVATE_KEY
        self.public_key = public_key or settings.VAPID_PUBLIC_KEY
        self.subject = subject or settings.VAPID_SUBJECT

    def is_configured(self) -> bool:
        return bool(self.private_key and self.public_key)

    async def send(self, channel: NotificationChannel, subject: str, body: str) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "VAPID not configured"
        try:
            keys = json.loads(channel.secret or "{}")
            endpoint = channel.target
            p256dh = keys.get("p256dh")
            auth = keys.get("auth")
            if not (endpoint and p256dh and auth):
                return False, "subscription keys missing"
            from pywebpush import webpush
            payload = json.dumps({
                "title": subject, "body": body,
                "url": settings.PUBLIC_BASE_URL + "/dashboard",
            })
            await asyncio.to_thread(
                webpush,
                subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
                data=payload,
                vapid_private_key=self.private_key,
                vapid_claims={"sub": self.subject},
            )
            return True, ""
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"


SENDERS: dict[str, Sender] = {
    "email": EmailSender(),
    "webpush": WebPushSender(),
}


def _in_quiet_hours(now: datetime, prefs: UserPreferences | None) -> bool:
    """True when `now` falls inside the user's quiet window (handles overnight ranges)."""
    if prefs is None or prefs.quiet_hours_start is None or prefs.quiet_hours_end is None:
        return False
    start: time = prefs.quiet_hours_start
    end: time = prefs.quiet_hours_end
    cur = now.timetz().replace(tzinfo=None) if hasattr(now, "timetz") else now.time()
    if start == end:
        return False
    if start < end:
        return start <= cur < end
    # overnight window, e.g. 22:00 -> 07:00
    return cur >= start or cur < end


def _get_prefs(db: Session, user_id: int) -> UserPreferences | None:
    return db.get(UserPreferences, user_id)


def list_channels(db: Session, user_id: int) -> list[NotificationChannel]:
    return list(db.execute(
        select(NotificationChannel).where(NotificationChannel.user_id == user_id)
        .order_by(NotificationChannel.created_at.desc())
    ).scalars())


def add_channel(db: Session, user: User, kind: str, target: str,
                subscription_keys: dict | None = None) -> NotificationChannel:
    if kind not in SENDERS:
        raise ValueError(f"unsupported channel kind: {kind}")
    secret = ""
    if kind == "webpush":
        if not subscription_keys:
            raise ValueError("webpush channels require subscription_keys (p256dh, auth)")
        secret = json.dumps(subscription_keys)
    # Web push endpoints are considered verified immediately because the
    # browser had to grant permission + we received the subscription from
    # the user's session. Email is verified separately (token in body).
    verified = (kind == "webpush")
    existing = db.execute(
        select(NotificationChannel).where(
            NotificationChannel.user_id == user.id,
            NotificationChannel.kind == kind,
            NotificationChannel.target == target,
        )
    ).scalar_one_or_none()
    if existing:
        existing.enabled = True
        existing.verified = existing.verified or verified
        if secret:
            existing.secret = secret
        db.commit()
        db.refresh(existing)
        return existing
    channel = NotificationChannel(user_id=user.id, kind=kind, target=target,
                                  secret=secret, verified=verified)
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel


def remove_channel(db: Session, user_id: int, channel_id: int) -> bool:
    ch = db.get(NotificationChannel, channel_id)
    if ch is None or ch.user_id != user_id:
        return False
    db.delete(ch)
    db.commit()
    return True


def set_channel_enabled(db: Session, user_id: int, channel_id: int, enabled: bool) -> NotificationChannel | None:
    ch = db.get(NotificationChannel, channel_id)
    if ch is None or ch.user_id != user_id:
        return None
    ch.enabled = enabled
    db.commit()
    db.refresh(ch)
    return ch


def company_name_for(db: Session, symbol: str) -> str:
    from app.models import WatchlistSymbol
    row = db.execute(
        select(WatchlistSymbol.display_name).where(WatchlistSymbol.symbol == symbol).limit(1)
    ).scalar_one_or_none()
    return row or symbol


def enqueue_alert(db: Session, user: User, alert: PriceAlert, triggered_value: float | None,
                  triggered_at: datetime) -> list[NotificationLog]:
    """Fan out a triggered alert to every enabled + verified channel.

    Always creates at least one NotificationLog row (even when there are no
    channels), so the in-app feed is the single source of truth for "what
    happened" regardless of external delivery.

    Network sends are *not* performed here: we just enqueue rows. The
    background worker (`deliver_pending`) drains them so the synchronous
    ingest path is never blocked on SMTP or push providers.
    """
    prefs = _get_prefs(db, user.id)
    if prefs is not None and not prefs.notification_enabled:
        return []
    quiet = _in_quiet_hours(triggered_at, prefs)
    payload = AlertPayload(
        alert_id=alert.id, symbol=alert.symbol, condition=alert.condition,
        threshold=alert.threshold, triggered_value=triggered_value,
        triggered_at=triggered_at, company_name=company_name_for(db, alert.symbol),
    )
    title, body = payload.title, payload.body

    channels = list(db.execute(
        select(NotificationChannel).where(
            NotificationChannel.user_id == user.id,
            NotificationChannel.enabled.is_(True),
            NotificationChannel.verified.is_(True),
        )
    ).scalars())

    if not channels:
        log = NotificationLog(
            user_id=user.id, alert_id=alert.id, kind="inapp",
            title=title, body=body, status="sent",
            sent_at=triggered_at,
            payload_json={"condition": alert.condition, "threshold": alert.threshold,
                          "triggered_value": triggered_value, "quiet_hours": quiet},
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return [log]

    if quiet and prefs is not None and getattr(prefs, "daily_digest", False):
        # One digest log row; actual digest delivery is a separate scheduled job (future).
        log = NotificationLog(
            user_id=user.id, alert_id=alert.id, kind="inapp",
            title=title, body=body, status="queued",
            payload_json={"condition": alert.condition, "threshold": alert.threshold,
                          "triggered_value": triggered_value, "quiet_hours": True,
                          "digest": True},
        )
        db.add(log)
        db.commit()
        return [log]

    out: list[NotificationLog] = []
    for channel in channels:
        log = NotificationLog(
            user_id=user.id, channel_id=channel.id, alert_id=alert.id,
            kind=channel.kind, title=title, body=body, status="queued",
            payload_json={"condition": alert.condition, "threshold": alert.threshold,
                          "triggered_value": triggered_value},
        )
        db.add(log)
        out.append(log)
    db.commit()
    return out


async def deliver_pending(db_factory: Callable[[], Session], max_concurrent: int = 8) -> int:
    """Background task: drain queued NotificationLog rows by calling their sender.

    `db_factory` is the app's SessionLocal (a no-arg callable) so this can run
    in a worker task without depending on request-scoped sessions.
    Returns the number of items processed.
    """
    db = db_factory()
    try:
        rows = list(db.execute(
            select(NotificationLog)
            .where(NotificationLog.status == "queued", NotificationLog.channel_id.isnot(None))
            .order_by(NotificationLog.created_at.asc())
            .limit(100)
        ).scalars())
        if not rows:
            return 0
        sem = asyncio.Semaphore(max_concurrent)

        async def _one(log: NotificationLog) -> None:
            async with sem:
                channel = db.get(NotificationChannel, log.channel_id)
                if channel is None or not channel.enabled:
                    log.status = "failed"
                    log.error = "channel missing or disabled"
                    return
                sender = SENDERS.get(channel.kind)
                if sender is None:
                    log.status = "failed"
                    log.error = f"no sender for kind={channel.kind}"
                    return
                ok, err = await sender.send(channel, log.title, log.body)
                log.status = "sent" if ok else "failed"
                log.error = err[:500]
                if ok:
                    log.sent_at = datetime.now(timezone.utc)
                    channel.last_used_at = log.sent_at

        await asyncio.gather(*(_one(r) for r in rows))
        db.commit()
        return len(rows)
    finally:
        db.close()