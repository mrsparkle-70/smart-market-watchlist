"""Pure, testable feature calculations. No I/O — the heart of 'meaningful change'."""
from __future__ import annotations

import math
from datetime import datetime, timezone


def pct_change(current: float, previous: float) -> float | None:
    if previous is None or previous == 0:
        return None
    return (current - previous) / previous * 100.0


def moving_average(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def daily_returns(closes: list[float]) -> list[float]:
    if len(closes) < 2:
        return []
    return [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1] != 0]


def realized_volatility(closes: list[float], window: int = 20, annualize: bool = True) -> float | None:
    """Std-dev of daily returns over `window` sessions, optionally annualized."""
    rets = daily_returns(closes)
    if len(rets) < window:
        return None
    sample = rets[-window:]
    mean = sum(sample) / len(sample)
    var = sum((r - mean) ** 2 for r in sample) / (len(sample) - 1)
    daily = math.sqrt(var)
    return daily * math.sqrt(252) if annualize else daily


def volatility_ratio(closes: list[float], window: int = 20) -> float | None:
    """current realized vol (last 5 sessions) / 20-day average vol. >1.5 = expansion."""
    rets = daily_returns(closes)
    if len(rets) < window + 5:
        return None
    recent = _window_vol(rets[-5:])
    baseline = _window_vol(rets[-(window + 5): -5])
    if baseline is None or baseline == 0 or recent is None:
        return None
    return recent / baseline


def _window_vol(rets: list[float]) -> float | None:
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(252)


def volume_ratio(current_volume: float | None, history_volumes: list[float], window: int = 20) -> float | None:
    """current volume / average volume over the same window (excludes current)."""
    if not current_volume or len(history_volumes) < 5:
        return None
    baseline = history_volumes[-window:]
    avg = sum(baseline) / len(baseline)
    if avg == 0:
        return None
    return current_volume / avg


def classify_freshness(source_timestamp: datetime | None, now: datetime | None = None, market_open: bool = True) -> str:
    """fresh <5min, delayed 5-30min, stale >30min during market hours, unknown otherwise."""
    if source_timestamp is None:
        return "unknown"
    now = now or datetime.now(timezone.utc)
    if source_timestamp.tzinfo is None:
        source_timestamp = source_timestamp.replace(tzinfo=timezone.utc)
    age_min = (now - source_timestamp).total_seconds() / 60
    if age_min < 0:
        # tolerate small clock skew between producer and consumer (up to 5 minutes)
        return "fresh" if age_min >= -5 else "unknown"

    if age_min < 5:
        return "fresh"
    if age_min < 30:
        return "delayed"
    return "stale" if market_open else "delayed"


def gap_pct(open_price: float | None, previous_close: float | None) -> float | None:
    if not open_price or not previous_close:
        return None
    return pct_change(open_price, previous_close)


def crossed_ma(closes: list[float], window: int) -> str | None:
    """Return 'crossed_above' / 'crossed_below' when the last close crossed its MA."""
    if len(closes) < window + 1:
        return None
    prev = closes[-2]
    curr = closes[-1]
    prev_ma = moving_average(closes[:-1], window)
    curr_ma = moving_average(closes, window)
    if prev_ma is None or curr_ma is None:
        return None
    if prev <= prev_ma and curr > curr_ma:
        return "crossed_above"
    if prev >= prev_ma and curr < curr_ma:
        return "crossed_below"
    return None
