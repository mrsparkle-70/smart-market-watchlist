"""Market Snapshot + Ingestion Service: pipeline steps 2-8 (section 10).

fetch -> normalize -> store snapshot -> compute features -> detect events ->
score -> dedupe -> persist. Fetch once per symbol, fan out to users (section 17).
"""
from __future__ import annotations

import hashlib
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import MarketEvent, MarketFeature, MarketSnapshot, NewsItem, PriceAlert, User, WatchlistSymbol
from app.providers.base import MarketDataProvider
from app.services import attention as A
from app.services import change_detection as CD
from app.services import explanation as E
from app.services import news as NEWS
from app.services.features import classify_freshness, pct_change


# The in-process scheduler and HTTP requests share the same SQLite database.
# Serialize ingestion so they cannot hold competing write transactions.
INGEST_LOCK = asyncio.Lock()


def get_last_snapshot(db: Session, symbol: str) -> MarketSnapshot | None:
    return db.execute(
        select(MarketSnapshot).where(MarketSnapshot.symbol == symbol)
        .order_by(MarketSnapshot.captured_at.desc()).limit(1)
    ).scalar_one_or_none()


async def _ingest_symbol(
    db: Session,
    provider: MarketDataProvider,
    symbol: str,
    thresholds: dict | None = None,
    now: datetime | None = None,
    benchmark_return: float | None = None,
    priority_tag: str = "normal",
) -> MarketEvent | None:
    """One pipeline pass for a symbol. Returns the highest-scored NEW event (if any)."""
    now = now or datetime.now(timezone.utc)
    th = thresholds or {}
    price_th = th.get("price_threshold", settings.DEFAULT_PRICE_THRESHOLD_PCT)
    volume_th = th.get("volume_threshold", settings.DEFAULT_VOLUME_THRESHOLD)
    vol_th = th.get("volatility_threshold", settings.DEFAULT_VOLATILITY_THRESHOLD)

    quote = await provider.get_quote(symbol)
    candles = await provider.get_ohlcv(symbol)
    freshness = classify_freshness(quote.source_timestamp, now, market_open=(quote.market_status == "open"))
    prev = get_last_snapshot(db, symbol)

    # Conflicting-provider guard: never silently overwrite another provider's value
    if prev is not None and prev.provider != quote.provider:
        deviation = abs(quote.price - prev.price) / prev.price if prev.price else 0
        data_quality = "conflicted" if deviation > 0.05 else freshness
    else:
        data_quality = freshness

    snapshot = MarketSnapshot(
        symbol=quote.symbol, provider=quote.provider, captured_at=now,
        price=quote.price, previous_close=quote.previous_close, open_price=quote.open_price,
        high_price=quote.high_price, low_price=quote.low_price, volume=quote.volume,
        currency=quote.currency, market_status=quote.market_status,
        source_timestamp=quote.source_timestamp, data_quality=data_quality,
        is_delayed=freshness in ("delayed", "stale"),
    )
    db.add(snapshot)
    db.flush()

    # Evaluate account-scoped alerts against the same normalized quote that is
    # being persisted. A one-hour cooldown prevents repeated notifications on
    # every pipeline tick while the condition remains true.
    move_pct = ((quote.price - quote.previous_close) / quote.previous_close * 100.0
                if quote.previous_close else 0.0)
    alert_rows = db.execute(select(PriceAlert).where(PriceAlert.symbol == quote.symbol, PriceAlert.enabled.is_(True))).scalars()
    triggered_alerts: list[PriceAlert] = []
    for alert in alert_rows:
        triggered = (
            (alert.condition == "price_above" and quote.price >= alert.threshold)
            or (alert.condition == "price_below" and quote.price <= alert.threshold)
            or (alert.condition == "move_up" and move_pct >= alert.threshold)
            or (alert.condition == "move_down" and move_pct <= -alert.threshold)
        )
        cooldown_ok = alert.last_triggered_at is None or (now - alert.last_triggered_at).total_seconds() >= 3600
        if triggered and cooldown_ok:
            alert.last_triggered_at = now
            alert.last_triggered_value = quote.price
            triggered_alerts.append(alert)
    # Persist alert state now so it survives even the baseline early-return path
    # below (prev is None), where the function returns before the main commit.
    db.flush()
    # Enqueue notification fan-out for any alerts that just fired.
    if triggered_alerts:
        from app.services import notify as N
        for alert in triggered_alerts:
            owner = db.get(User, alert.user_id)
            if owner is not None:
                N.enqueue_alert(db, owner, alert, quote.price, now)

    candle_closes = [c.close for c in candles]
    candle_volumes = [c.volume for c in candles]
    feats = CD.compute_features(
        quote_price=quote.price, quote_open=quote.open_price, quote_previous_close=quote.previous_close,
        quote_volume=quote.volume, candle_closes=candle_closes, candle_volumes=candle_volumes,
        prev_snapshot_price=prev.price if prev else None,
        benchmark_return=benchmark_return,
    )
    db.add(MarketFeature(symbol=quote.symbol, captured_at=now, **feats))

    # First pass = baseline only: without a previous snapshot there is no "change
    # since last check" to detect, and quoting history alone creates false events.
    if prev is None:
        db.commit()
        return None

    # Stale-data rule: show last known value, never generate new events (section 11)
    if data_quality == "stale":
        db.commit()
        return None

    detections = CD.detect_events(
        feats, price_threshold=price_th, volume_threshold=volume_th, volatility_threshold=vol_th,
        closes=candle_closes + [quote.price],
    )

    # ---- News impact (section 5): filter and score, never an unranked list ----
    try:
        articles = await provider.get_news(symbol, since=prev.captured_at if prev else None)
    except Exception:
        articles = []
    for art in articles:
        h = hashlib.sha256(f"{art.headline}|{art.source}".encode()).hexdigest()
        exists = db.execute(select(NewsItem).where(NewsItem.content_hash == h).limit(1)).scalars().first()
        relevance, sentiment = NEWS.score_article(art.headline, art.source, art.published_at)
        if exists is None:
            db.add(NewsItem(
                symbol=quote.symbol, source=art.source, url=art.url, headline=art.headline,
                published_at=art.published_at, content_hash=h, relevance_score=relevance,
                sentiment_label=sentiment, raw_metadata_json={},
            ))
        if relevance >= 30:
            detections.append(CD.Detection(
                event_type="news_impact",
                title=f"News: {art.headline[:90]}",
                evidence={"trigger": f"news relevance {relevance:.0f}/100 ({sentiment} tone)",
                          "baseline": "keyword + source-reliability filter", "current": art.headline,
                          "window": "since previous snapshot", "source": art.source},
                news_relevance=relevance,
                dedupe_suffix=h[:10],
            ))

    # ---- Personal threshold (section 14): your own bar for watched names ----
    change = feats.get("return_since_previous_snapshot")
    if priority_tag == "high_priority" and change is not None and 1.0 <= abs(change) < price_th:
        detections.append(CD.Detection(
            event_type="personal_threshold",
            title=f"{quote.symbol} moved {change:+.1f}% — on your personal watch",
            evidence={"trigger": f"personal threshold: |{change:+.1f}%| at high-priority tag "
                                 f"(standard bar is {price_th}%)",
                      "baseline": f"user threshold {price_th}% / 2", "current": f"{change:+.1f}%",
                      "window": "since previous snapshot", "source": "user preference"},
        ))

    # Corporate/fundamental events (section 5: high priority)
    try:
        corp_events = await provider.get_corporate_events(symbol)
    except Exception:
        corp_events = []
    day_bucket = now.strftime("%Y%m%d")
    corp = [
        CD.Detection(
            event_type=ce.event_type,
            title=ce.title,
            evidence={"trigger": f"{ce.event_type} reported by provider", "baseline": "provider event feed",
                      "current": ce.title, "window": "since previous snapshot",
                      "details": ce.details},
        )
        for ce in corp_events
        if ce.effective_at is None or (now - ce.effective_at).total_seconds() < 86400 * 3
    ]
    detections.extend(corp)

    confidence = A.estimate_confidence(
        freshness=freshness, volume=quote.volume is not None, history_days=len(candle_closes),
    )
    # Corroborating signals across categories make a change meaningful (section 5):
    sig_components = sum(
        1 for v in (
            A.price_score(feats.get("return_since_previous_snapshot"), price_th),
            A.volume_score(feats.get("volume_ratio"), volume_th),
            A.volatility_score(feats.get("volatility_ratio"), vol_th),
            A.relative_performance_score(feats.get("relative_return")),
        ) if v > 0
    )
    # By-design meaningful events: catalysts and user-driven alerts earn real estate
    # even when their star-only score would fall into "background" (sections 5, 6, 14).
    IMPORTANT_TYPES = {
        "earnings", "earnings_surprise", "guidance_change", "merger_acquisition",
        "stock_split", "dividend_change", "analyst_change", "personal_threshold",
        "gap", "ma_break", "relative_move",
    }
    IMPORTANT_FLOOR = 50.0  # attention floor -> ~43 final at typical confidence

    best_event: MarketEvent | None = None
    for det in detections:
        day_bucket = now.strftime("%Y%m%d")  # one event per type per symbol per day
        key = CD.build_dedupe_key(quote.symbol, det.event_type, day_bucket + det.dedupe_suffix)
        existing = db.execute(
            select(MarketEvent).where(MarketEvent.dedupe_key == key).limit(1)
        ).scalars().first()
        if existing:
            continue

        score = A.compute_attention_score(
            event_type=det.event_type, change_pct=feats.get("return_since_previous_snapshot"),
            price_threshold=price_th, volume_ratio_value=feats.get("volume_ratio"),
            volume_threshold=volume_th, vol_ratio=feats.get("volatility_ratio"),
            volatility_threshold=vol_th, relative_return=feats.get("relative_return"),
            news_relevance=det.news_relevance,
            detected_at=now, now=now,
        )
        if det.event_type in IMPORTANT_TYPES or (det.event_type == "news_impact" and det.news_relevance >= 70):
            score = max(score, IMPORTANT_FLOOR)
        fscore = A.final_score(score, confidence)
        severity = A.severity_for(fscore)
        if sig_components >= 2:
            # corroborated multi-signal moves are never "background" (section 5)
            severity = "notable" if severity == "background" else severity
        event = MarketEvent(
            symbol=quote.symbol, event_type=det.event_type, detected_at=now, effective_at=now,
            attention_score=score, confidence_score=confidence, final_score=fscore,
            severity=severity, title=det.title,
            summary=E.explain_event(
                quote.symbol, change_since_visit=feats.get("return_since_previous_snapshot"),
                volume_ratio_value=feats.get("volume_ratio"), relative_return=feats.get("relative_return"),
                event_type=det.event_type, event_title=det.title,
            ),
            evidence_json={
                "trigger": det.evidence.get("trigger", ""),
                "baseline": det.evidence.get("baseline", "20-session baseline"),
                "current": det.evidence.get("change_pct", det.evidence.get("volume_ratio", "")),
                "window": det.evidence.get("window", "since previous snapshot"),
                "source": f"{quote.provider} @ {quote.source_timestamp or now}",
                "confidence": confidence,
                "features": feats,
            },
            dedupe_key=key,
        )
        db.add(event)
        db.flush()
        if best_event is None or event.final_score > best_event.final_score:
            best_event = event

    db.commit()
    return best_event


async def _ingest_watchlist(db: Session, provider: MarketDataProvider, watchlist_id: int,
                           benchmark_return: float | None = None) -> dict:
    """Poll every unique symbol once; results fan out to all users watching them.

    `benchmark_return` may be passed in (computed once per pipeline cycle) so that
    multiple watchlists share a consistent market-relative baseline.
    """
    rows = db.execute(select(WatchlistSymbol.symbol, WatchlistSymbol.priority_tag)
                      .where(WatchlistSymbol.watchlist_id == watchlist_id)).all()
    tags = {sym: tag for sym, tag in rows}
    symbols = list(tags.keys())

    # Benchmark context for market-relative returns (section 5)
    bench_ret = benchmark_return
    bsym = settings.BENCHMARK_SYMBOL
    if bench_ret is None and bsym and bsym.upper() not in tags:
        prev_bench = get_last_snapshot(db, bsym.upper())
        bq = await provider.get_quote(bsym)
        if prev_bench is not None and prev_bench.price:
            bench_ret = pct_change(bq.price, prev_bench.price)
        await _ingest_symbol(db, provider, bsym)

    results: dict = {}
    for sym in symbols:
        try:
            evt = await _ingest_symbol(db, provider, sym, benchmark_return=bench_ret,
                                      priority_tag=tags.get(sym, "normal"))
            results[sym] = evt.final_score if evt else 0.0
        except Exception as exc:  # provider failure must not kill the pipeline (section 19)
            results[sym] = f"error: {exc}"
    return results


async def ingest_symbol(*args, **kwargs) -> MarketEvent | None:
    """Run one symbol ingestion pass without competing with another pass."""
    async with INGEST_LOCK:
        return await _ingest_symbol(*args, **kwargs)


async def ingest_watchlist(*args, **kwargs) -> dict:
    """Run a watchlist ingestion pass without competing with the scheduler."""
    async with INGEST_LOCK:
        return await _ingest_watchlist(*args, **kwargs)
