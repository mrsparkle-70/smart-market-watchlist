from __future__ import annotations
from app.providers.base import MarketDataProvider  # noqa: F401
from app.providers.mock import MockMarketDataProvider  # noqa: F401

# One provider instance per process: simulated state (or HTTP connection pool)
# must survive across requests so demo shocks and baselines behave consistently.
_provider_instance: MarketDataProvider | None = None


def get_provider() -> MarketDataProvider:
    """Provider registry/factory. Add vendors here without touching services."""
    global _provider_instance
    if _provider_instance is None:
        from app.core.config import settings

        if settings.MARKET_DATA_PROVIDER == "finnhub":
            from app.providers.finnhub import FinnhubProvider

            _provider_instance = FinnhubProvider()
        else:
            _provider_instance = MockMarketDataProvider()
    return _provider_instance
