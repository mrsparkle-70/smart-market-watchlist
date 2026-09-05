"""Background data pipeline (section 10).

Scheduler -> fetch -> normalize -> snapshot -> features -> events -> rank.
MVP: in-process asyncio loop started with the FastAPI app.
Production: move to Celery/Dramatiq beat without changing ingest_symbol().
"""
from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.core.database import SessionLocal
from app.providers import get_provider
from app.services.ingest import ingest_watchlist
from sqlalchemy import select

from app.models import Watchlist

logger = logging.getLogger("pipeline")


async def poll_all_watchlists() -> None:
    """One polling pass across every watchlist (dedupes work per symbol)."""
    db = SessionLocal()
    try:
        provider = get_provider()
        watchlist_ids = [w[0] for w in db.execute(select(Watchlist.id)).all()]
        for wl_id in watchlist_ids:
            results = await ingest_watchlist(db, provider, wl_id)
            for sym, res in results.items():
                if isinstance(res, str) and res.startswith("error"):
                    logger.warning("ingest failed watchlist=%s symbol=%s: %s", wl_id, sym, res)
    finally:
        db.close()


async def run_pipeline(stop_event: asyncio.Event) -> None:
    interval = max(60, settings.POLL_INTERVAL_SECONDS)
    logger.info("pipeline started (interval=%ss)", interval)
    while not stop_event.is_set():
        try:
            await poll_all_watchlists()
        except Exception:  # never let one bad cycle kill the worker
            logger.exception("pipeline cycle failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
    logger.info("pipeline stopped")


def start_pipeline() -> asyncio.Task | None:
    if not settings.PIPELINE_ENABLED:
        return None
    # Started from within the FastAPI lifespan (an async context), so a running
    # loop is guaranteed. asyncio.create_task is the supported API on 3.10+;
    # get_event_loop() is deprecated and can fail when no loop is running.
    stop_event = asyncio.Event()
    return asyncio.create_task(run_pipeline(stop_event))
