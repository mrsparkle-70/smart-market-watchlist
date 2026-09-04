"""Change Detection Service (section 9): features -> events -> scores. Mostly pure = testable."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services import features as F
from app.services import attention as A


@dataclass
class Detection:
    event_type: str
    title: str
    evidence: dict[str, Any] = field(default_factory=dict)
    news_relevance: float = 0.0   # set for news_impact detections (feeds news_score)
    dedupe_suffix: str = ""       # extra uniqueness for per-article events


def compute_features(
    *,
    quote_price: float,
    quote_open: float | None,
    quote_previous_close: float,
    quote_volume: float | None,
    candle_closes: list[float],
    candle_volumes: list[float],
    prev_snapshot_price: float | None = None,
    benchmark_return: float | None = None,
) -> dict[str, Any]:
    """Normalize provider data into the MarketFeature vector (section 8)."""
    closes = candle_closes + [quote_price]  # current quote is the newest data point
    feats: dict[str, Any] = {
        "return_1d": F.pct_change(quote_price, quote_previous_close),
        "return_since_previous_snapshot": F.pct_change(quote_price, prev_snapshot_price) if prev_snapshot_price else None,
        "volume_ratio": F.volume_ratio(quote_volume, candle_volumes),
        "volatility_20d": F.realized_volatility(candle_closes, 20),
        "volatility_ratio": F.volatility_ratio(candle_closes),
        "ma_20": F.moving_average(closes, 20),
        "ma_50": F.moving_average(closes, 50),
        "ma_200": F.moving_average(closes, 200),
        "gap_pct": F.gap_pct(quote_open, quote_previous_close),
        "relative_return": None,
    }
    # Market-relative movement (section 5): stock move minus benchmark move over the
    # same window (both since their previous snapshots). Sector context beats absolutes.
    stock_ret = feats["return_since_previous_snapshot"]
    if benchmark_return is not None and stock_ret is not None:
        feats["relative_return"] = stock_ret - benchmark_return
    return feats


def detect_events(
    feats: dict[str, Any],
    *,
    price_threshold: float = 3.0,
    volume_threshold: float = 2.0,
    volatility_threshold: float = 1.5,
    gap_threshold: float = 2.0,
    relative_threshold: float = 1.5,
    vol_multiplier: float = 1.5,
    closes: list[float] | None = None,
) -> list[Detection]:
    """Signal categories from section 5. Each detection carries its evidence."""
    detections: list[Detection] = []

    change = feats.get("return_since_previous_snapshot")
    vol20 = feats.get("volatility_20d") or 0.0
    # Price movement: absolute OR statistically large vs historical volatility
    price_trig = None
    if change is not None:
        if abs(change) >= price_threshold:
            price_trig = f"absolute return {change:+.1f}% >= {price_threshold}% threshold"
        elif vol20 > 0:
            daily_sigma = vol20 / (252 ** 0.5)
            move_in_sigma = abs(change) / (daily_sigma * 100) if daily_sigma else 0
            if move_in_sigma >= vol_multiplier:
                price_trig = f"move equals {move_in_sigma:.1f} historical standard deviations (>={vol_multiplier})"
    if price_trig:
        detections.append(Detection(
            "price_move",
            f"{feats.get('symbol', 'Symbol')} moved {change:+.1f}%",
            {"trigger": price_trig, "change_pct": change, "threshold_pct": price_threshold,
             "volatility_20d": vol20},
        ))

    vr = feats.get("volume_ratio")
    if vr is not None and vr >= volume_threshold:
        detections.append(Detection(
            "unusual_volume",
            f"Volume {vr:.1f}x normal",
            {"trigger": f"volume ratio {vr:.2f} >= {volume_threshold}", "volume_ratio": vr,
             "baseline": "20-session average volume"},
        ))

    vratio = feats.get("volatility_ratio")
    if vratio is not None and vratio >= volatility_threshold:
        detections.append(Detection(
            "volatility_spike",
            f"Volatility expanded to {vratio:.1f}x baseline",
            {"trigger": f"volatility ratio {vratio:.2f} >= {volatility_threshold}",
             "volatility_20d": vol20},
        ))

    if closes:
        for window in (20, 50, 200):
            cross = F.crossed_ma(closes, window)
            if cross:
                ma_now = F.moving_average(closes, window)
                detections.append(Detection(
                    "ma_break",
                    f"{'Crossed above' if cross == 'crossed_above' else 'Crossed below'} {window}-day moving average",
                    {"trigger": cross, "window": f"{window}d", "ma_value": ma_now, "price": closes[-1]},
                ))

    gap = feats.get("gap_pct")
    if gap is not None and abs(gap) >= gap_threshold:
        detections.append(Detection(
            "gap",
            f"Gap {'up' if gap > 0 else 'down'} {abs(gap):.1f}% at open",
            {"trigger": f"|gap| {abs(gap):.1f}% >= {gap_threshold}%", "gap_pct": gap},
        ))

    rel = feats.get("relative_return")
    stock_ret = feats.get("return_since_previous_snapshot")
    if rel is not None and abs(rel) >= relative_threshold:
        # Only call it a rotation when the benchmark actually moved; a stock moving
        # while the market is flat is a price move, not relative strength.
        bench_moved = stock_ret is not None and abs(stock_ret - rel) >= 0.75
        if bench_moved:
            detections.append(Detection(
                "relative_move",
                f"{'Outperforming' if rel > 0 else 'Underperforming'} benchmark by {abs(rel):.1f} pts",
                {"trigger": f"|relative return| {abs(rel):.1f} >= {relative_threshold} pts "
                            f"(benchmark moved {stock_ret - rel:+.1f} pts)",
                 "relative_return": rel},
            ))

    return detections


def build_dedupe_key(symbol: str, event_type: str, bucket: str) -> str:
    """Deduplicate repeated events within the same time bucket (section 9)."""
    return f"{symbol}:{event_type}:{bucket}"
