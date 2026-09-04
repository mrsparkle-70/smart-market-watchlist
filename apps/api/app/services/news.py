"""News filter (section 5): score articles instead of displaying an unranked list.

Relevance = symbol keywords + event keywords + source reliability + recency.
Sentiment is a label, never presented as fact.
"""
from __future__ import annotations

from datetime import datetime, timezone

EVENT_KEYWORDS = {
    "earnings": 30, "beats": 25, "misses": 25, "guidance": 30, "raises": 15, "cuts": 20,
    "upgrade": 25, "downgrade": 30, "merger": 35, "acquisition": 35, "buyout": 35,
    "lawsuit": 25, "probe": 25, "recall": 30, "buyback": 20, "dividend": 15,
    "split": 25, "insider": 20, "sec": 25, "fda": 30, "strike": 15, "shortage": 20,
}
RELIABLE_SOURCES = ("reuters", "bloomberg", "wsj", "ft", "cnbc", "associated press", "barron's")


def score_article(headline: str, source: str, published_at: datetime | None = None) -> tuple[float, str]:
    """Return (relevance 0..100, sentiment_label). Deterministic keyword scoring."""
    text = headline.lower()
    relevance = 25.0  # base: it matched the symbol feed at all
    relevance += min(30.0, sum(weight for kw, weight in EVENT_KEYWORDS.items() if kw in text))
    if any(s in (source or "").lower() for s in RELIABLE_SOURCES):
        relevance += 15.0
    if published_at is not None:
        age_h = max((datetime.now(timezone.utc) - published_at.replace(tzinfo=published_at.tzinfo or timezone.utc)).total_seconds() / 3600, 0)
        if age_h < 24:
            relevance += 15.0
        elif age_h < 72:
            relevance += 7.0
    relevance = min(100.0, relevance)

    positive = ("beats", "raises", "upgrade", "record", "surge", "buyback", "wins", "strong")
    negative = ("misses", "cuts", "downgrade", "lawsuit", "probe", "recall", "falls", "weak", "probe")
    pos = sum(1 for w in positive if w in text)
    neg = sum(1 for w in negative if w in text)
    sentiment = "positive" if pos > neg else "negative" if neg > pos else "neutral"
    return round(relevance, 1), sentiment
