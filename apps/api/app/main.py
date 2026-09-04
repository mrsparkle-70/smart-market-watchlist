"""Smart Market Watchlist API — FastAPI application entrypoint."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import attention, auth, demo, market, portfolio, watchlists
from app.core.config import settings, _env_file
from app.core.database import init_db
from app.workers.pipeline import start_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("smw")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = start_pipeline()
    logger.info("API started (provider=%s, env=%s)", settings.MARKET_DATA_PROVIDER, settings.ENV)
    yield
    if task:
        task.cancel()


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
app.include_router(demo.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "provider": settings.MARKET_DATA_PROVIDER}


@app.get("/api/debug/config")
def debug_config():
    """Debug endpoint to verify configuration is loaded correctly."""
    return {
        "status": "ok",
        "env_file_found": _env_file is not None,
        "env_file_path": _env_file,
        "settings": {
            "APP_NAME": settings.APP_NAME,
            "ENV": settings.ENV,
            "CORS_ORIGINS": settings.CORS_ORIGINS,
            "DATABASE_URL": settings.DATABASE_URL[:50] + "..." if len(settings.DATABASE_URL) > 50 else settings.DATABASE_URL,
            "REDIS_URL": settings.REDIS_URL if settings.REDIS_URL else "(not set)",
            "MARKET_DATA_PROVIDER": settings.MARKET_DATA_PROVIDER,
            "MARKET_DATA_API_KEY": "SET" if settings.MARKET_DATA_API_KEY else "(not set)",
            "JWT_SECRET": "SET" if settings.JWT_SECRET else "(not set)",
            "POLL_INTERVAL_SECONDS": settings.POLL_INTERVAL_SECONDS,
            "PIPELINE_ENABLED": settings.PIPELINE_ENABLED,
            "LLM_API_KEY": "SET" if settings.LLM_API_KEY else "(not set)",
        },
    }
