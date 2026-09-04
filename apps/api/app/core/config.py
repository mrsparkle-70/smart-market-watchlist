"""Application configuration via environment variables (pydantic-settings)."""
from __future__ import annotations
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "Smart Market Watchlist API"
    ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- Persistence ---
    DATABASE_URL: str = "sqlite:///./watchlist.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Auth ---
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # --- Market data provider ---
    # "mock" = deterministic simulated provider (hackathon/demo, no key needed)
    # "finnhub" = licensed real provider (requires FINNHUB_API_KEY)
    MARKET_DATA_PROVIDER: str = "mock"
    MARKET_DATA_API_KEY: str = ""
    MARKET_DATA_BASE_URL: str = ""
    BENCHMARK_SYMBOL: str = "SPY"

    # --- Background pipeline ---
    POLL_INTERVAL_SECONDS: int = 300
    PIPELINE_ENABLED: bool = True

    # --- Default change-detection thresholds ---
    DEFAULT_PRICE_THRESHOLD_PCT: float = 3.0
    DEFAULT_VOLUME_THRESHOLD: float = 2.0
    DEFAULT_VOLATILITY_THRESHOLD: float = 1.5
    DEFAULT_GAP_THRESHOLD_PCT: float = 2.0
    HISTORICAL_VOL_MULTIPLIER: float = 1.5

    # --- Optional LLM (explanation rewriting only; never used for truth) ---
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_MODEL: str = "openai/gpt-oss-20b"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
