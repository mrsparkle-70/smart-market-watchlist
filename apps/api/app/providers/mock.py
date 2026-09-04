"""Deterministic simulated provider. Zero API key needed — hackathon/demo mode.

Supports scripted "demo storyline" shocks:
    provider.apply_shock("NVDA", pct=5.8, volume_multiplier=2.3)
    provider.add_corporate_event("MSFT", "earnings", "Q3 earnings beat", ...)
"""
from __future__ import annotations

import random
import zlib
from datetime import datetime, timedelta, timezone

from app.providers.base import (
    Candle,
    CompanyProfile,
    CorporateEvent,
    NewsArticle,
    Quote,
)

PROFILES = {
    "AAPL": CompanyProfile("AAPL", "Apple Inc.", "NASDAQ", "Technology", "Consumer Electronics"),
    "NVDA": CompanyProfile("NVDA", "NVIDIA Corporation", "NASDAQ", "Technology", "Semiconductors"),
    "MSFT": CompanyProfile("MSFT", "Microsoft Corporation", "NASDAQ", "Technology", "Software"),
    "TSLA": CompanyProfile("TSLA", "Tesla, Inc.", "NASDAQ", "Consumer Cyclical", "Auto Manufacturers"),
    "AMZN": CompanyProfile("AMZN", "Amazon.com, Inc.", "NASDAQ", "Consumer Cyclical", "Internet Retail"),
    "GOOGL": CompanyProfile("GOOGL", "Alphabet Inc.", "NASDAQ", "Technology", "Internet Content"),
    "META": CompanyProfile("META", "Meta Platforms, Inc.", "NASDAQ", "Technology", "Internet Content"),
    "SPY": CompanyProfile("SPY", "SPDR S&P 500 ETF Trust", "NYSEARCA", "Index", "ETF"),
}

# Broader demo/search universe. Live providers are not limited to this list;
# these profiles make the no-key mock mode useful beyond the original examples.
ADDITIONAL_COMPANIES = [
    ("GOOG", "Alphabet Inc."), ("AVGO", "Broadcom Inc."), ("BRK.B", "Berkshire Hathaway Inc."),
    ("JPM", "JPMorgan Chase & Co."), ("V", "Visa Inc."), ("MA", "Mastercard Incorporated"),
    ("UNH", "UnitedHealth Group Incorporated"), ("XOM", "Exxon Mobil Corporation"),
    ("JNJ", "Johnson & Johnson"), ("WMT", "Walmart Inc."), ("PG", "Procter & Gamble Co."),
    ("HD", "The Home Depot, Inc."), ("CVX", "Chevron Corporation"), ("ABBV", "AbbVie Inc."),
    ("KO", "The Coca-Cola Company"), ("PEP", "PepsiCo, Inc."), ("COST", "Costco Wholesale Corporation"),
    ("MRK", "Merck & Co., Inc."), ("BAC", "Bank of America Corporation"), ("CRM", "Salesforce, Inc."),
    ("AMD", "Advanced Micro Devices, Inc."), ("ORCL", "Oracle Corporation"), ("NFLX", "Netflix, Inc."),
    ("ADBE", "Adobe Inc."), ("CSCO", "Cisco Systems, Inc."), ("ACN", "Accenture plc"),
    ("TMO", "Thermo Fisher Scientific Inc."), ("MCD", "McDonald's Corporation"), ("DIS", "The Walt Disney Company"),
    ("NKE", "NIKE, Inc."), ("LIN", "Linde plc"), ("ABT", "Abbott Laboratories"),
    ("DHR", "Danaher Corporation"), ("VZ", "Verizon Communications Inc."), ("CMCSA", "Comcast Corporation"),
    ("TXN", "Texas Instruments Incorporated"), ("QCOM", "QUALCOMM Incorporated"), ("INTU", "Intuit Inc."),
    ("AMGN", "Amgen Inc."), ("IBM", "International Business Machines Corporation"), ("CAT", "Caterpillar Inc."),
    ("GE", "GE Aerospace"), ("RTX", "RTX Corporation"), ("BA", "The Boeing Company"),
    ("LLY", "Eli Lilly and Company"), ("PFE", "Pfizer Inc."), ("COP", "ConocoPhillips"),
    ("UPS", "United Parcel Service, Inc."), ("LOW", "Lowe's Companies, Inc."), ("SBUX", "Starbucks Corporation"),
    ("GILD", "Gilead Sciences, Inc."), ("MDLZ", "Mondelez International, Inc."), ("ISRG", "Intuitive Surgical, Inc."),
    ("NOW", "ServiceNow, Inc."), ("AMAT", "Applied Materials, Inc."), ("PANW", "Palo Alto Networks, Inc."),
    ("MU", "Micron Technology, Inc."), ("ADI", "Analog Devices, Inc."), ("BKNG", "Booking Holdings Inc."),
    ("TJX", "The TJX Companies, Inc."), ("DE", "Deere & Company"), ("SYK", "Stryker Corporation"),
    ("C", "Citigroup Inc."), ("GS", "The Goldman Sachs Group, Inc."), ("MS", "Morgan Stanley"),
    ("BLK", "BlackRock, Inc."), ("SCHW", "The Charles Schwab Corporation"), ("T", "AT&T Inc."),
    ("LMT", "Lockheed Martin Corporation"), ("PLD", "Prologis, Inc."), ("AMT", "American Tower Corporation"),
    ("SO", "The Southern Company"), ("DUK", "Duke Energy Corporation"), ("NEE", "NextEra Energy, Inc."),
    ("OXY", "Occidental Petroleum Corporation"), ("SLB", "SLB"), ("EOG", "EOG Resources, Inc."),
    ("MAR", "Marriott International, Inc."), ("HLT", "Hilton Worldwide Holdings Inc."), ("ABNB", "Airbnb, Inc."),
    ("UBER", "Uber Technologies, Inc."), ("LYFT", "Lyft, Inc."), ("SHOP", "Shopify Inc."),
    ("SQ", "Block, Inc."), ("PYPL", "PayPal Holdings, Inc."), ("COIN", "Coinbase Global, Inc."),
    ("RBLX", "Roblox Corporation"), ("SNAP", "Snap Inc."), ("PINS", "Pinterest, Inc."),
    ("SPOT", "Spotify Technology S.A."), ("TGT", "Target Corporation"), ("CVS", "CVS Health Corporation"),
    ("GM", "General Motors Company"), ("F", "Ford Motor Company"), ("FDX", "FedEx Corporation"),
    ("DAL", "Delta Air Lines, Inc."), ("AAL", "American Airlines Group Inc."), ("RIVN", "Rivian Automotive, Inc."),
    ("PDD", "PDD Holdings Inc."), ("TSM", "Taiwan Semiconductor Manufacturing Company Limited"),
]
PROFILES.update({
    symbol: CompanyProfile(symbol, name, "NASDAQ", "Market", "Stock")
    for symbol, name in ADDITIONAL_COMPANIES
})


class MockMarketDataProvider:
    name = "mock"

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
        self._prices: dict[str, float] = {}
        self._base: dict[str, float] = {}
        self._day_volume: dict[str, float] = {}
        self._volume_multiplier: dict[str, float] = {}
        self._gap: dict[str, float] = {}          # one-shot open gap (pct)
        self._events: dict[str, list[CorporateEvent]] = {}
        self._news: list[NewsArticle] = []
        self._history: dict[str, list[Candle]] = {}
        self._pinned: set[str] = set()  # history locked by force_ma_cross

    def _ensure_symbol(self, symbol: str) -> None:
        symbol = symbol.upper()
        if symbol in self._prices:
            return
        base = {"SPY": 550.0}.get(symbol, 100.0 + self._rng.random() * 400.0)
        self._base[symbol] = base
        self._prices[symbol] = base
        self._day_volume[symbol] = 5_000_000 + self._rng.random() * 20_000_000
        self._volume_multiplier[symbol] = 1.0

    # ---- demo controls -------------------------------------------------
    def apply_shock(self, symbol: str, pct: float, volume_multiplier: float = 1.0) -> None:
        """Simulate a sudden meaningful move (e.g. NVDA +5.8% on 2.3x volume)."""
        self._ensure_symbol(symbol)
        symbol = symbol.upper()
        self._prices[symbol] *= 1 + pct / 100
        self._volume_multiplier[symbol] = volume_multiplier

    def set_gap(self, symbol: str, pct: float) -> None:
        """Engineer tomorrow's (next quote's) open gap vs previous close."""
        self._ensure_symbol(symbol)
        self._gap[symbol.upper()] = pct

    def force_ma_cross(self, symbol: str, direction: str) -> None:
        """Engineer the price to cross its 20-day MA in the given direction, pinned."""
        self._ensure_symbol(symbol)
        symbol = symbol.upper()
        hist = self._get_history(symbol)
        closes = [c.close for c in hist]
        ma20 = sum(closes[-20:]) / 20
        # park the last candle just below (for a cross above) the MA
        closes[-1] = ma20 * (0.994 if direction == "above" else 1.006)
        hist[-1] = Candle(ts=hist[-1].ts, open=hist[-1].open, high=max(hist[-1].high, closes[-1]),
                          low=min(hist[-1].low, closes[-1]), close=closes[-1], volume=hist[-1].volume)
        self._history[symbol] = hist[-120:]
        self._prices[symbol] = ma20 * (1.012 if direction == "above" else 0.988)
        self._volume_multiplier[symbol] = 1.4
        self._pinned.add(symbol)

    def next_tick(self) -> None:
        """Advance one polling cycle: small random walk, decaying volume shock."""
        for sym in self._prices:
            drift = self._rng.gauss(0, 0.004)
            self._prices[sym] *= 1 + drift
            self._volume_multiplier[sym] = 1.0 + (self._volume_multiplier[sym] - 1.0) * 0.5


    def add_corporate_event(self, symbol: str, event_type: str, title: str, details: dict | None = None) -> CorporateEvent:
        evt = CorporateEvent(
            symbol=symbol,
            event_type=event_type,
            title=title,
            effective_at=datetime.now(timezone.utc),
            details=details or {},
        )
        self._events.setdefault(symbol.upper(), []).append(evt)
        return evt

    def add_news(self, article: NewsArticle) -> None:
        self._news.append(article)

    # ---- MarketDataProvider interface -----------------------------------
    def _get_history(self, symbol: str, lookback: int = 210) -> list[Candle]:
        """Deterministic OHLCV history anchored to the current live price.

        The cache is re-anchored whenever the price has moved meaningfully since the
        last candle close (e.g. after a scenario shock) so MAs and quote are consistent.
        Pinned histories (force_ma_cross) are always returned as-is.
        """
        symbol = symbol.upper()
        self._ensure_symbol(symbol)
        cached = self._history.get(symbol)
        if symbol in self._pinned and cached:
            return cached[-lookback:]
        if cached is not None:
            last_close = cached[-1].close
            dev = abs(self._prices[symbol] - last_close) / last_close if last_close else 1
            if dev < 0.003:  # price unchanged (~0.3%): stable baseline, reuse
                return cached[-lookback:]
        # (Re)generate anchored at the current live price, walking backwards
        rng = random.Random(zlib.crc32((symbol + str(int(self._prices[symbol] * 1000))).encode()))
        candles: list[Candle] = []
        price = self._prices[symbol]
        now = datetime.now(timezone.utc)
        for i in range(lookback, 0, -1):
            change = rng.gauss(0.0004, 0.010)
            o = price
            c = price / (1 + change)  # invert: walk backwards through prior closes
            if i > 1:
                h = max(o, c) * (1 + abs(rng.gauss(0, 0.003)))
                low = min(o, c) * (1 - abs(rng.gauss(0, 0.003)))
            else:
                h, low = o, c
            vol = self._day_volume[symbol] * rng.uniform(0.85, 1.15)
            candles.append(Candle(ts=now - timedelta(days=i), open=round(o, 4), high=round(h, 4),
                                  low=round(low, 4), close=round(c, 4), volume=round(vol)))
            price = c
        candles.reverse()  # chronological
        self._history[symbol] = candles
        return candles[-lookback:]

    async def get_quote(self, symbol: str) -> Quote:
        symbol = symbol.upper()
        self._ensure_symbol(symbol)
        price = self._prices[symbol]
        prev_close = price / 1.001  # intraday: previous close ~ current before drift
        open_price = price * 0.999
        gap = self._gap.pop(symbol, None)
        if gap is not None:
            open_price = prev_close * (1 + gap / 100)  # engineered gap at open
        return Quote(
            symbol=symbol,
            price=round(price, 4),
            previous_close=round(prev_close, 4),
            open_price=round(open_price, 4),
            high_price=round(max(price, open_price) * 1.002, 4),
            low_price=round(min(price, open_price) * 0.998, 4),
            volume=self._day_volume[symbol] * self._volume_multiplier[symbol],
            market_status="open",
            source_timestamp=datetime.now(timezone.utc),
            provider=self.name,
        )

    async def get_ohlcv(self, symbol: str, interval: str = "1d", lookback_days: int = 120) -> list[Candle]:
        return self._get_history(symbol.upper(), lookback_days)

    async def get_company_profile(self, symbol: str) -> CompanyProfile:
        symbol = symbol.upper()
        return PROFILES.get(symbol, CompanyProfile(symbol, symbol, "NASDAQ", "Unknown", "Unknown"))

    async def get_corporate_events(self, symbol: str) -> list[CorporateEvent]:
        return list(self._events.get(symbol.upper(), []))

    async def get_news(self, symbol: str, since: datetime | None = None) -> list[NewsArticle]:
        if since is not None and since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)  # SQLite returns naive datetimes
        return [n for n in self._news if n.symbol == symbol.upper() and (since is None or n.published_at >= since)]

    async def search_symbol(self, query: str) -> list[CompanyProfile]:
        q = query.upper()
        return [p for p in PROFILES.values() if q in p.symbol or q in p.name.upper()]
