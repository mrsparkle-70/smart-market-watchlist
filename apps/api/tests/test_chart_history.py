"""Feature #3: price-history chart API (roadmap #41 + #42)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.models import MarketSnapshot

from tests.conftest import register_and_login


def _add_snapshots(symbol: str, stamps_prices: list[tuple[datetime, float]]) -> None:
    db = SessionLocal()
    try:
        for ts, price in stamps_prices:
            db.add(MarketSnapshot(
                symbol=symbol, provider="mock", captured_at=ts, price=price,
                previous_close=price, volume=1000,
            ))
        db.commit()
    finally:
        db.close()


def _add_symbol_to_watchlist(client) -> None:
    r = client.post("/api/watchlists", json={"name": "Chart"})
    assert r.status_code in (200, 201), r.text
    wl = r.json()
    r = client.post(f"/api/watchlists/{wl['id']}/symbols", json={"symbol": "NVDA"})
    assert r.status_code in (200, 201), r.text


def test_history_returns_most_recent_window_oldest_first(client):
    """With more snapshots than the limit, the chart must show the NEWEST data
    (asc+limit would return the oldest rows and hide recent prices forever)."""
    register_and_login(client)
    _add_symbol_to_watchlist(client)

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    stamps_prices = [
        (base + timedelta(minutes=i), 100.0 + i) for i in range(30)
    ]
    _add_snapshots("NVDA", stamps_prices)

    r = client.get("/api/market/NVDA/history?limit=10")
    assert r.status_code == 200
    candles = r.json()
    assert len(candles) == 10
    # Oldest → newest, and the window is the most recent one (prices 120..129).
    assert [c["close"] for c in candles] == [120.0 + i for i in range(10)]
    ts_list = [c["ts"] for c in candles]
    assert ts_list == sorted(ts_list), "history must be oldest → newest"


def test_history_dedupes_same_second_snapshots(client):
    """Duplicate-safe ingestion (#42): two snapshots captured in the same second
    collapse to one chart point; the newest price wins."""
    register_and_login(client)
    _add_symbol_to_watchlist(client)

    base = datetime(2026, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
    stamps_prices = [
        (base, 50.0),
        (base + timedelta(microseconds=400_000), 51.0),  # same second → deduped
        (base + timedelta(seconds=1), 52.0),
    ]
    _add_snapshots("NVDA", stamps_prices)

    candles = client.get("/api/market/NVDA/history").json()
    assert len(candles) == 2
    assert [c["close"] for c in candles] == [51.0, 52.0]
    # Strictly ascending unique per-second timestamps (lightweight-charts contract).
    seconds = [c["ts"][:19] for c in candles]
    assert len(set(seconds)) == len(seconds)


def test_history_still_blocks_unauthenticated_and_non_watched(client):
    # Auth boundary fires first, then watchlist ownership (#16).
    assert client.get("/api/market/NVDA/history").status_code == 401
    register_and_login(client)
    assert client.get("/api/market/NVDA/history").status_code == 404
