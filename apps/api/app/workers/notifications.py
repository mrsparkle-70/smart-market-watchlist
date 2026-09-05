"""Background drain for queued NotificationLog rows (feature #1)."""
from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.core.database import SessionLocal
from app.services import notify as N

logger = logging.getLogger("smw.notif.worker")

INTERVAL_SECONDS = 10


async def _loop(stop_event: asyncio.Event) -> None:
    logger.info("notification worker started (interval=%ss)", INTERVAL_SECONDS)
    while not stop_event.is_set():
        try:
            processed = await N.deliver_pending(SessionLocal)
            if processed:
                logger.info("delivered %d notification(s)", processed)
        except Exception:
            logger.exception("notification worker cycle failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            pass
    logger.info("notification worker stopped")


def start_notification_worker() -> asyncio.Task | None:
    # Honor the same kill switch as the data pipeline; in tests/CI the worker
    # would otherwise race with conftest's drop_all teardown and crash.
    if not settings.PIPELINE_ENABLED:
        return None
    stop_event = asyncio.Event()
    return asyncio.create_task(_loop(stop_event))
