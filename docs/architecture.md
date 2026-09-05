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

## Persistence, migrations & backups (feature #2)

The API runs on **Postgres in production** (`postgresql+psycopg2://...` via
`DATABASE_URL`) and keeps **SQLite for local dev/tests** (`sqlite:///...`).

**Schema management — Alembic.** Migrations live in `apps/api/alembic/versions/`.
On startup, `init_db()` detects a Postgres URL and runs `upgrade head` before
serving, so a deployed container always matches the checked-in history. SQLite
keeps `create_all` (dev convenience). Migration tests (`tests/test_migrations.py`)
fail on drift: `upgrade head` must build exactly the tables in `Base.metadata`.

```bash
cd apps/api
# author a migration after model changes:
ALEMBIC_DATABASE_URL='sqlite:///./_gen.db' .venv/bin/alembic revision --autogenerate -m '...'
# manual apply / inspect:
ALEMBIC_DATABASE_URL='postgresql+psycopg2://...' .venv/bin/alembic upgrade head
ALEMBIC_DATABASE_URL='postgresql+psycopg2://...' .venv/bin/alembic current
```

**Backups.** `python -m app.tools.backup` (from `apps/api/`):
- Postgres → `pg_dump --format=custom` archives (restore with `pg_restore -d ... <file>`)
- SQLite → online copy via SQLite's backup API (safe while the API runs)
- `--keep N` prunes old files (default 7); `--list` shows what exists;
  `BACKUP_DIR` overrides the output directory (default `<repo>/backups/`, gitignored)

In Docker, `docker compose run --rm db-backup` produces the same pg_dump archive
into `./backups/` without entering the API container.

**Engine hygiene.** `pool_pre_ping` is on for both dialects; Postgres uses an
explicit `QueuePool` (5 + 10 overflow) so the asyncio workers can't exhaust
connections silently.

## Scaling path (section 17)

- Redis shared quote cache + request dedupe (single-flight per symbol)
- Queue-based ingestion with separate event-detection workers
- Postgres indexes on `(symbol, captured_at)` / `(symbol, detected_at)`
- Partition processing per symbol; time-series storage for high-frequency data
