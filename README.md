# Smart Market Watchlist

> "What meaningfully changed since I last checked, and what deserves my attention now?"

Instead of a price grid, this product builds a personalized **change brief**: ranked,
explainable attention cards combining market data, historical baselines, event detection,
freshness metadata, and user-specific state.

## Quick start (local, no API key needed)

```bash
# Backend (Python 3.9+)
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# Interactive API docs: http://localhost:8000/api/docs

# Frontend (Node 18+)
cd apps/web
npm install
npm run dev
# App: http://localhost:3000  (API is proxied to :8000)
```

The default `MARKET_DATA_PROVIDER=mock` is a deterministic simulator — no market-data key
required. Register an account, add symbols (AAPL, NVDA, MSFT, TSLA…), press
**Refresh market data** to build a baseline, then visit later to see your change brief.

### Full stack with Docker

```bash
cp .env.example .env   # optional: set FINNHUB / LLM keys
docker compose up --build
```

## Architecture

```
Browser → Next.js (app router, TanStack Query, lightweight-charts)
             │ REST / SSE
             ▼
         FastAPI
           ├── Auth service (argon2 + JWT httpOnly cookie)
           ├── Watchlist service (ownership-checked CRUD)
           ├── Snapshot service  (normalize + persist provider data)
           ├── Change detection  (pure feature/threshold engine)
           ├── Attention scoring (weighted, confidence-adjusted, explainable)
           └── Explanation service (deterministic templates; optional LLM rewrite)
                ▼
        PostgreSQL + Redis        Background pipeline (in-process asyncio loop)
                                          ▼
                                MarketDataProvider adapter (mock | finnhub)
```

Key design decisions (see `docs/`):

- **Raw data ≠ snapshots ≠ events ≠ user state.** Each layer is a separate table, which
  makes the system explainable and testable.
- **Fetch once per symbol, fan out to users.** The pipeline polls symbols, not users.
- **Everything is explainable.** Every card carries trigger, baseline, current value,
  window, source, and confidence. No mysterious AI scores.
- **LLM is presentation-only.** Deterministic templates are the fallback; the optional
  LLM only rewrites verified structured facts and is never allowed to invent causes.
- **Stale data never triggers events.** Freshness (`fresh|delayed|stale|unknown`) is
  stored per snapshot and shown in the UI.

## Demo storyline (section 23)

1. Register, add AAPL / NVDA / MSFT, press **Refresh market data** (baseline).
2. The dashboard records your visit — cards are empty by design.
3. Simulate changes while away: in Python, `provider.apply_shock("NVDA", 5.8, 2.3)` +
   `provider.add_corporate_event("MSFT", "earnings_surprise", ...)`, or just press
   **Refresh market data** after injecting a scenario.
4. Reload: *"2 meaningful changes since your last visit"* — NVDA (price+volume, explainable
   evidence) and MSFT (earnings). AAPL's normal drift stays invisible.
5. Mark reviewed → your *next* visit shows only genuinely new information.

## Tests

```bash
cd apps/api
.venv/bin/python -m pytest tests/ -q   # 56 tests: features, scoring, detection, auth,
                                       # watchlists, notifications, migrations, chart history,
                                       # E2E demo
```

## Repository layout

```
apps/api      FastAPI backend (providers, services, workers, tests)
apps/web      Next.js frontend (app/, components/, lib/)
docs/         architecture, API reference, product decisions
infra/        reserved for deployment manifests
```
