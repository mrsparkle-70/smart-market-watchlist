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


# --- Relative performance vs benchmark (roadmap #46) -------------------

def _add_benchmarks(symbol: str, stamps_prices: list[tuple[datetime, float]]) -> None:
    _add_snapshots(symbol, stamps_prices)


def test_relative_rebases_to_zero_and_aligns_days(client):
    register_and_login(client)
    _add_symbol_to_watchlist(client)

    base = datetime(2026, 3, 2, tzinfo=timezone.utc)  # Monday
    # NVDA: 100 → 110 → 121  (+0%, +10%, +21%)
    _add_snapshots("NVDA", [(base + timedelta(days=d, hours=10), p) for d, p in
                            [(0, 100.0), (1, 110.0), (2, 121.0)]])
    # SPY: 400 → 440 → 396  (+0%, +10%, -1%); captured at a different hour
    _add_benchmarks("SPY", [(base + timedelta(days=d, hours=14), p) for d, p in
                            [(0, 400.0), (1, 440.0), (2, 396.0)]])

    r = client.get("/api/market/NVDA/relative")
    assert r.status_code == 200
    data = r.json()
    assert data["benchmark"] == "SPY"
    points = data["points"]
    assert len(points) == 3
    assert [p["date"] for p in points] == ["2026-03-02", "2026-03-03", "2026-03-04"]
    assert [p["symbol_pct"] for p in points] == [0.0, 10.0, 21.0]
    assert [p["benchmark_pct"] for p in points] == [0.0, 10.0, -1.0]


def test_relative_uses_last_close_of_each_day(client):
    """Multiple snapshots per day must collapse to the day's LAST close."""
    register_and_login(client)
    _add_symbol_to_watchlist(client)

    base = datetime(2026, 3, 9, tzinfo=timezone.utc)
    _add_snapshots("NVDA", [
        (base, 100.0),
        (base + timedelta(hours=5), 105.0),   # intraday point, superseded
        (base + timedelta(hours=7), 102.0),   # last close of day 1
        (base + timedelta(days=1), 110.0),
    ])
    _add_benchmarks("SPY", [(base, 400.0), (base + timedelta(days=1), 400.0)])

    points = client.get("/api/market/NVDA/relative").json()["points"]
    # Base = day-1 LAST close (102): 110/102 - 1 = +7.843%, and the 105 intraday
    # point must not leak into the base or the series.
    assert len(points) == 2
    assert points[0]["symbol_pct"] == 0.0
    assert points[1]["symbol_pct"] == 7.843


def test_relative_empty_when_benchmark_has_no_data(client):
    register_and_login(client)
    _add_symbol_to_watchlist(client)
    base = datetime(2026, 3, 2, tzinfo=timezone.utc)
    _add_snapshots("NVDA", [(base, 100.0), (base + timedelta(days=1), 101.0)])

    data = client.get("/api/market/NVDA/relative").json()
    assert data["benchmark"] == "SPY"
    assert data["points"] == []


def test_relative_rejects_self_benchmark_and_non_watched(client):
    register_and_login(client)
    _add_symbol_to_watchlist(client)
    # Benchmark identical to symbol → 400.
    assert client.get("/api/market/NVDA/relative?benchmark=NVDA").status_code == 400
    # Unwatched symbol → 404 (ownership boundary still applies).
    assert client.get("/api/market/MSFT/relative").status_code == 404
    assert client.get("/api/market/NVDA/relative").status_code == 200

