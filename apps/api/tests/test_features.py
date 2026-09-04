"""Unit tests: feature calculations and staleness classification (section 19)."""
from datetime import datetime, timedelta, timezone

from app.services import features as F


def test_pct_change():
    assert F.pct_change(110, 100) == 10.0
    assert F.pct_change(90, 100) == -10.0
    assert F.pct_change(100, 0) is None


def test_moving_average():
    assert F.moving_average([1, 2, 3, 4, 5], 5) == 3.0
    assert F.moving_average([1, 2], 5) is None


def test_realized_volatility_positive():
    closes = [100 + ((-1) ** i) * i for i in range(30)]
    vol = F.realized_volatility(closes, 20)
    assert vol is not None and vol > 0


def test_volume_ratio():
    history = [1_000_000.0] * 20
    assert F.volume_ratio(2_500_000, history) == 2.5
    assert F.volume_ratio(None, history) is None
    assert F.volume_ratio(100, []) is None


def test_freshness_classification():
    now = datetime.now(timezone.utc)
    assert F.classify_freshness(now - timedelta(minutes=1), now) == "fresh"
    assert F.classify_freshness(now - timedelta(minutes=10), now) == "delayed"
    assert F.classify_freshness(now - timedelta(minutes=45), now, market_open=True) == "stale"
    assert F.classify_freshness(now - timedelta(minutes=45), now, market_open=False) == "delayed"
    assert F.classify_freshness(None, now) == "unknown"
    assert F.classify_freshness(now + timedelta(minutes=10), now) == "unknown"  # big future ts
    assert F.classify_freshness(now + timedelta(seconds=30), now) == "fresh"  # tiny clock skew


def test_gap_pct():
    assert abs(F.gap_pct(104.0, 100.0) - 4.0) < 1e-9
    assert F.gap_pct(None, 100.0) is None


def test_ma_cross_detection():
    # price falls below its 20-day MA on the last bar
    closes = [100.0] * 20 + [99.0]
    assert F.crossed_ma(closes, 20) == "crossed_below"
    closes_up = [100.0] * 20 + [101.0]
    assert F.crossed_ma(closes_up, 20) == "crossed_above"
    closes_flat = [100.0] * 22
    assert F.crossed_ma(closes_flat, 20) is None
