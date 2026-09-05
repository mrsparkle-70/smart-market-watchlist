"""Application configuration via environment variables (pydantic-settings)."""
from __future__ import annotations
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> str | None:
    """Search for .env file in current and parent directories."""
    current = Path.cwd()
    for _ in range(4):
        env_path = current / ".env"
        if env_path.exists():
            return str(env_path)
        current = current.parent
    return None


_env_file = _find_env_file()


# Well-known placeholder secrets that must never be used in production.
_INSECURE_JWT_SECRETS = {"change-me-in-production", "dev-secret-change-me", "test-secret"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        extra="ignore",
    )

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

    # --- Optional LLM ---
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_MODEL: str = "openai/gpt-oss-20b"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Fail fast in production if the JWT secret is still a public placeholder:
    # signing tokens with a well-known secret lets anyone forge auth cookies.
    if settings.ENV == "production" and settings.JWT_SECRET in _INSECURE_JWT_SECRETS:
        raise RuntimeError(
            "JWT_SECRET is set to an insecure default while ENV=production. "
            "Set a strong, unique JWT_SECRET before starting the API."
        )
    return settings


settings = get_settings()
