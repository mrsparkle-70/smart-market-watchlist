"""Unit tests: attention scoring bands and confidence (section 6)."""
from datetime import datetime, timedelta, timezone

from app.services import attention as A


def test_price_score_respects_threshold():
    assert A.price_score(2.0, 3.0) == 0.0
    assert A.price_score(3.0, 3.0) > 0
    assert A.price_score(9.0, 3.0) == A.WEIGHTS["price"]  # capped at 3x threshold
    assert A.price_score(-5.0, 3.0) == A.price_score(5.0, 3.0)  # symmetric


def test_volume_score():
    assert A.volume_score(1.5, 2.0) == 0.0
    assert A.volume_score(2.0, 2.0) > 0
    assert A.volume_score(20.0, 2.0) == A.WEIGHTS["volume"]


def test_event_score_ranking():
    assert A.event_score("earnings_surprise") > A.event_score("price_move") == 0
    assert A.event_score("merger_acquisition") > A.event_score("dividend_change")


def test_total_score_bounded_and_banded():
    now = datetime.now(timezone.utc)
    big = A.compute_attention_score(
        event_type="earnings_surprise", change_pct=8.0, volume_ratio_value=4.0,
        vol_ratio=2.5, relative_return=4.0, news_relevance=80, detected_at=now, now=now,
    )
    assert 0 <= big <= 100
    assert A.severity_for(big) == "investigate"
    small = A.compute_attention_score(event_type="price_move", change_pct=0.5,
                                      detected_at=now, now=now)
    assert A.severity_for(small) == "background"


def test_personal_preference_adjusts():
    now = datetime.now(timezone.utc)
    base = dict(event_type="price_move", change_pct=5.0, detected_at=now, now=now)
    high = A.compute_attention_score(**base, priority_tag="high_priority")
    ignore = A.compute_attention_score(**base, priority_tag="ignore_short_term")
    assert high > ignore


def test_confidence_and_final_score():
    assert A.estimate_confidence(freshness="fresh") > A.estimate_confidence(freshness="stale")
    assert A.final_score(90.0, 0.5) == 45.0
    assert A.final_score(90.0, 1.2) == 90.0  # confidence capped at 1


def test_recency_decay():
    now = datetime.now(timezone.utc)
    fresh = A.recency_score(now - timedelta(hours=1), now)
    old = A.recency_score(now - timedelta(hours=30), now)
    assert fresh == 10.0 * (23 / 24)
    assert old == 0.0
