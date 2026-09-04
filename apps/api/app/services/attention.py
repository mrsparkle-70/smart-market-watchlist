"""Attention scoring (section 6). Transparent, weighted, confidence-adjusted.

attention_score = weighted components (0..100)
final_score     = attention_score * data_confidence
Priority bands: 80-100 investigate, 60-79 review, 35-59 notable, 0-34 background.
"""
from __future__ import annotations

WEIGHTS = {
    "price": 25.0,
    "volume": 15.0,
    "volatility": 10.0,
    "event": 25.0,
    "news": 15.0,
    "relative": 10.0,
}

EVENT_TYPE_BASE_SCORE = {
    # Corporate/fundamental events get high priority (section 5)
    "earnings": 90.0,
    "earnings_surprise": 95.0,
    "guidance_change": 85.0,
    "dividend_change": 55.0,
    "stock_split": 70.0,
    "insider_transaction": 50.0,
    "merger_acquisition": 95.0,
    "analyst_change": 60.0,
    "news_impact": 45.0,
    # Technical/statistical events start from zero and earn their score
    "price_move": 0.0,
    "unusual_volume": 0.0,
    "volatility_spike": 0.0,
    "ma_break": 0.0,
    "gap": 0.0,
    "relative_move": 0.0,
    "personal_threshold": 40.0,
}

SEVERITY_BANDS = ((80.0, "investigate"), (60.0, "review"), (35.0, "notable"), (0.0, "background"))


def price_score(change_pct: float | None, threshold_pct: float) -> float:
    """0..25. Scales linearly up to 3x the user threshold."""
    if change_pct is None:
        return 0.0
    magnitude = abs(change_pct)
    if magnitude < threshold_pct:
        return 0.0
    ratio = min(magnitude / threshold_pct, 3.0)  # cap at 3x threshold
    return WEIGHTS["price"] * (ratio / 3.0)


def volume_score(volume_ratio_value: float | None, threshold: float = 2.0) -> float:
    """0..15. Scales from threshold (0) to 5x threshold (full)."""
    if volume_ratio_value is None or volume_ratio_value < threshold:
        return 0.0
    ratio = min(volume_ratio_value / (threshold * 5.0), 1.0)
    return WEIGHTS["volume"] * ratio


def volatility_score(vol_ratio: float | None, threshold: float = 1.5) -> float:
    """0..10."""
    if vol_ratio is None or vol_ratio < threshold:
        return 0.0
    ratio = min((vol_ratio - threshold) / (threshold * 2.0), 1.0)
    return WEIGHTS["volatility"] * ratio


def event_score(event_type: str) -> float:
    """0..25 — normalized base score of corporate/fundamental events."""
    base = EVENT_TYPE_BASE_SCORE.get(event_type, 0.0)
    return WEIGHTS["event"] * (base / 100.0)


def news_score(relevance: float) -> float:
    """0..15 — relevance_score in 0..100 from the news filter."""
    if relevance <= 0:
        return 0.0
    return WEIGHTS["news"] * min(relevance / 100.0, 1.0)


def relative_performance_score(relative_return: float | None, threshold_pct: float = 1.5) -> float:
    """0..10 — out/under-performance vs benchmark, benchmark-relative beats absolute."""
    if relative_return is None or abs(relative_return) < threshold_pct:
        return 0.0
    ratio = min(abs(relative_return) / (threshold_pct * 3.0), 1.0)
    return WEIGHTS["relative"] * ratio


def recency_score(detected_at, now) -> float:
    """0..10 bonus — decays over 24 hours."""
    age_hours = max((now - detected_at).total_seconds() / 3600, 0)
    return max(0.0, 10.0 * (1 - age_hours / 24))


def personal_preference_score(priority_tag: str) -> float:
    """User-told relevance adjusts the score (section 14: personal relevance)."""
    return {
        "high_priority": 10.0,
        "speculative": 5.0,
        "normal": 0.0,
        "long_term": -2.0,
        "ignore_short_term": -15.0,
    }.get(priority_tag, 0.0)


def noise_penalty(num_similar_events: int) -> float:
    """Group related events; each redundant sibling slightly penalizes."""
    return max(0.0, num_similar_events - 1) * 2.5


def compute_attention_score(
    *,
    event_type: str,
    change_pct: float | None = None,
    price_threshold: float = 3.0,
    volume_ratio_value: float | None = None,
    volume_threshold: float = 2.0,
    vol_ratio: float | None = None,
    volatility_threshold: float = 1.5,
    relative_return: float | None = None,
    news_relevance: float = 0.0,
    detected_at=None,
    now=None,
    priority_tag: str = "normal",
    similar_events: int = 0,
) -> float:
    score = 0.0
    score += price_score(change_pct, price_threshold)
    score += volume_score(volume_ratio_value, volume_threshold)
    score += volatility_score(vol_ratio, volatility_threshold)
    score += event_score(event_type)
    score += news_score(news_relevance)
    score += relative_performance_score(relative_return)
    if detected_at is not None and now is not None:
        score += recency_score(detected_at, now)
    score += personal_preference_score(priority_tag)
    score -= noise_penalty(similar_events)
    return round(max(0.0, min(100.0, score)), 2)


def final_score(attention: float, data_confidence: float) -> float:
    """Never display a mysterious score: confidence multiplies, reasons travel with it."""
    return round(max(0.0, min(100.0, attention * max(0.0, min(1.0, data_confidence)))), 2)


def severity_for(score: float) -> str:
    for floor, label in SEVERITY_BANDS:
        if score >= floor:
            return label
    return "background"


def estimate_confidence(*, freshness: str, volume: bool = True, history_days: int = 120) -> float:
    """Data confidence in 0..1 from freshness, completeness, and history depth."""
    conf = 1.0
    conf *= {"fresh": 1.0, "delayed": 0.7, "stale": 0.4, "unknown": 0.3}.get(freshness, 0.5)
    if not volume:
        conf *= 0.8
    if history_days < 30:
        conf *= 0.6
    elif history_days < 100:
        conf *= 0.85
    return round(max(0.1, min(1.0, conf)), 2)
