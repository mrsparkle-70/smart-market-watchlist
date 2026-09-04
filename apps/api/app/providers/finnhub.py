"""Finnhub adapter (licensed provider). Enabled with MARKET_DATA_PROVIDER=finnhub + API key.

Kept behind the same MarketDataProvider interface so vendors are swappable.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from zoneinfo import ZoneInfo

import httpx

from app.core.config import settings
from app.providers.base import (
    Candle,
    CompanyProfile,
    CorporateEvent,
    NewsArticle,
    Quote,
)

BASE_URL = settings.MARKET_DATA_BASE_URL or "https://finnhub.io/api/v1"
logger = logging.getLogger("smw.finnhub")


def _market_status(now: datetime | None = None) -> str:
    """Return a lightweight NYSE session status for quote freshness display."""
    ny = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo("America/New_York"))
    if ny.weekday() >= 5:
        return "closed"
    minutes = ny.hour * 60 + ny.minute
    if 570 <= minutes < 960:  # 09:30–16:00 ET
        return "open"
    if 240 <= minutes < 570:  # 04:00–09:30 ET
        return "pre"
    if 960 <= minutes < 1200:  # 16:00–20:00 ET
        return "after"
    return "closed"


class FinnhubProvider:
    name = "finnhub"

    def __init__(self, api_key: str | None = None, client: httpx.AsyncClient | None = None):
        self._api_key = api_key or settings.MARKET_DATA_API_KEY
        self._client = client or httpx.AsyncClient(base_url=BASE_URL, timeout=10)

    def _params(self, **extra) -> dict:
        return {"token": self._api_key, **extra}

    async def get_quote(self, symbol: str) -> Quote:
        r = await self._client.get("/quote", params=self._params(symbol=symbol))
        r.raise_for_status()
        d = r.json()
        if not d.get("c"):
            raise ValueError(f"no quote data for {symbol}")
        return Quote(
            symbol=symbol.upper(),
            price=float(d["c"]),
            previous_close=float(d.get("pc") or d["c"]),
            high_price=float(d["h"]) if d.get("h") else None,
            low_price=float(d["l"]) if d.get("l") else None,
            open_price=float(d["o"]) if d.get("o") else None,
            source_timestamp=datetime.fromtimestamp(d["t"], tz=timezone.utc) if d.get("t") else None,
            market_status=_market_status(),
            provider=self.name,
        )

    async def get_ohlcv(self, symbol: str, interval: str = "1d", lookback_days: int = 120) -> list[Candle]:
        end = int(datetime.now(timezone.utc).timestamp())
        start = end - lookback_days * 86400
        r = await self._client.get(
            "/stock/candle",
            params=self._params(symbol=symbol, resolution="D", **{"from": str(start), "to": str(end)}),
        )
        if r.status_code == 403:
            # Some Finnhub keys permit quotes but not historical candles. Keep
            # the live quote path usable; price/gap changes still work, while
            # history-dependent signals are intentionally unavailable.
            logger.warning("Finnhub historical candles unavailable for %s (403); continuing quote-only", symbol)
            return []
        r.raise_for_status()
        d = r.json()
        if d.get("s") != "ok":
            return []
        return [
            Candle(
                ts=datetime.fromtimestamp(t, tz=timezone.utc),
                open=o, high=h, low=low, close=c, volume=v,
            )
            for t, o, h, low, c, v in zip(d["t"], d["o"], d["h"], d["l"], d["c"], d["v"])
        ]

    async def get_company_profile(self, symbol: str) -> CompanyProfile:
        r = await self._client.get("/stock/profile2", params=self._params(symbol=symbol))
        r.raise_for_status()
        d = r.json()
        return CompanyProfile(
            symbol=symbol.upper(),
            name=d.get("name") or symbol.upper(),
            exchange=d.get("exchange") or "",
            industry=d.get("finnhubIndustry") or "",
        )

    async def get_corporate_events(self, symbol: str) -> list[CorporateEvent]:
        today = datetime.now(timezone.utc)
        r = await self._client.get(
            "/calendar/earnings",
            params=self._params(**{"from": (today - timedelta(days=1)).date().isoformat(), "to": today.date().isoformat()}),
        )
        r.raise_for_status()
        events: list[CorporateEvent] = []
        for e in r.json().get("earningsCalendar", []):
            if e.get("symbol") == symbol.upper():
                events.append(
                    CorporateEvent(
                        symbol=symbol.upper(),
                        event_type="earnings",
                        title="Earnings announcement",
                        effective_at=today,
                        details={"eps_actual": e.get("epsActual"), "eps_estimate": e.get("epsEstimate")},
                    )
                )
        return events

    async def get_news(self, symbol: str, since: datetime | None = None) -> list[NewsArticle]:
        today = datetime.now(timezone.utc).date()
        r = await self._client.get(
            "/company-news",
            params=self._params(
                symbol=symbol,
                **{"from": (today - timedelta(days=3)).isoformat()},
                to=today.isoformat(),
            ),
        )
        r.raise_for_status()
        articles: list[NewsArticle] = []
        for a in r.json():
            published = datetime.fromtimestamp(a.get("datetime", 0), tz=timezone.utc)
            if since and published < since:
                continue
            articles.append(
                NewsArticle(
                    symbol=symbol.upper(),
                    headline=a.get("headline", ""),
                    source=a.get("source", ""),
                    url=a.get("url", ""),
                    published_at=published,
                )
            )
        return articles

    async def search_symbol(self, query: str) -> list[CompanyProfile]:
        r = await self._client.get("/search", params=self._params(q=query))
        r.raise_for_status()
        return [
            CompanyProfile(symbol=item["symbol"], name=item.get("description", ""), exchange=item.get("type", ""))
            for item in r.json().get("result", [])[:10]
        ]
