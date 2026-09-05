"""Smart Market Watchlist API — FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import attention, auth, demo, market, notifications, portfolio, watchlists
from app.core.config import settings
from app.core.database import init_db
from app.workers.pipeline import start_pipeline
from app.workers.notifications import start_notification_worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smw")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = start_pipeline()
    notif_task = start_notification_worker()
    logger.info("API started (provider=%s, env=%s)", settings.MARKET_DATA_PROVIDER, settings.ENV)
    yield
    for t in (task, notif_task):
        if t:
            t.cancel()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(auth.router)
app.include_router(watchlists.router)
app.include_router(portfolio.router)
app.include_router(market.router)
app.include_router(attention.router)
app.include_router(notifications.router)
app.include_router(demo.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "provider": settings.MARKET_DATA_PROVIDER}
