# Architecture

## Layers of truth

The core separation (section 3 of the product plan):

1. **Raw provider responses** — never shown directly; each snapshot stores provider name,
   source timestamp, ingestion time, market status, and data quality.
2. **Normalized market snapshots** (`market_snapshots`) — comparable across time.
3. **Derived features** (`market_features`) — returns, volume ratio, volatility, MAs,
   gaps, benchmark-relative returns. Pure functions in `app/services/features.py`.
4. **Detected events** (`market_events`) — thresholded, deduplicated (one event per
   symbol/type/day), scored, explained.
5. **User-specific state** (`user_event_state`) — seen / reviewed / dismissed / saved.
   Loading the dashboard never marks anything reviewed.

## Data pipeline (section 10)

```
Scheduler (asyncio loop / Celery beat in production)
  → Fetch jobs (provider adapter)
  → Normalize + validate + classify freshness
  → Store snapshot
  → Compute features (pure functions)
  → Detect events (thresholds + statistical triggers)
  → Score (weighted components × data confidence)
  → Deduplicate → Persist → Attention feed query
```

MVP polling: 5–15 min market hours, 30–60 min after hours, nightly recalculation.
Never fetch the same quote per user — fetch per symbol and fan out.

## Scoring

`final = Σ(weighted components) × data_confidence`, weights per the plan:
price 25%, corporate event 25%, news 15%, volume 15%, relative performance 10%,
volatility 10%, plus a recency bonus and personal-relevance adjustment. An event with
≥2 corroborating signal categories is never ranked "background" — corroboration is the
product's definition of meaningful.

## Swapping vendors

Implement the `MarketDataProvider` protocol (`app/providers/base.py`) and register the
class in `app/providers/__init__.py`. Frontend and services never import a vendor SDK.

## Scaling path (section 17)

- Redis shared quote cache + request dedupe (single-flight per symbol)
- Queue-based ingestion with separate event-detection workers
- Postgres indexes on `(symbol, captured_at)` / `(symbol, detected_at)`
- Partition processing per symbol; time-series storage for high-frequency data
