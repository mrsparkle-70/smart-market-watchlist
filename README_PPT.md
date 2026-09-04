# Smart Market Watchlist — Project Documentation

> **"What meaningfully changed since I last checked, and what deserves my attention now?"**

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [The Problem We Solve](#2-the-problem-we-solve)
3. [Core Idea & Philosophy](#3-core-idea--philosophy)
4. [Architecture](#4-architecture)
5. [Technology Stack](#5-technology-stack)
6. [Key Components & Why They Exist](#6-key-components--why-they-exist)
7. [Data Flow Pipeline](#7-data-flow-pipeline)
8. [Scoring System](#8-scoring-system)
9. [Change Detection](#9-change-detection)
10. [User Visit Tracking](#10-user-visit-tracking)
11. [Explanation Service](#11-explanation-service)
12. [Provider Abstraction](#12-provider-abstraction)
13. [Database Design](#13-database-design)
14. [API Design](#14-api-design)
15. [Frontend Architecture](#15-frontend-architecture)
16. [Security & Privacy](#16-security--privacy)
17. [Testing Strategy](#17-testing-strategy)
18. [Demo Storyline](#18-demo-storyline)
19. [Product Decisions](#19-product-decisions)
20. [Feature Roadmap](#20-feature-roadmap)
21. [Scaling Path](#21-scaling-path)
22. [How to Run](#22-how-to-run)

---

## 1. Project Overview

**Smart Market Watchlist** is a personalized market monitoring platform that replaces traditional price grids with **intelligent change briefs**. Instead of showing users raw stock prices, it answers:

> *"What meaningfully changed since I last checked, and what deserves my attention now?"*

### What It Does
- Tracks user watchlists of stock symbols
- Detects meaningful market changes using multi-signal analysis
- Ranks changes by attention score with explainable evidence
- Presents a personalized "change brief" on each visit
- Allows users to mark events as reviewed, dismissed, or saved

### What Makes It Different
| Traditional Watchlist | Smart Market Watchlist |
|----------------------|----------------------|
| Shows raw prices | Shows meaningful changes |
| No context | Explainable evidence for every alert |
| Noise-heavy | Corroboration-based filtering |
| Static grid | Personalized, visit-aware feed |
| Opaque | Transparent scoring with confidence |

---

## 2. The Problem We Solve

### The Information Overload Problem
Modern investors face:
- **Too much data**: Hundreds of price movements across watchlists
- **No prioritization**: All changes appear equally important
- **No context**: Why did something change? Is it significant?
- **Repetitive noise**: Same alerts firing repeatedly
- **No memory**: Systems don't remember what you've already seen

---

## 3. Core Idea & Philosophy

### The "Change Brief" Concept
Instead of a price grid, the product builds a **personalized change brief**:
- **Ranked**: Most important changes first
- **Explainable**: Every card shows why it matters
- **Visit-aware**: Only shows what changed since your last visit
- **Actionable**: Mark reviewed, dismiss, or save

### Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Raw data ≠ snapshots ≠ events ≠ user state** | Each layer is a separate table |
| **Fetch once per symbol, fan out to users** | Pipeline polls symbols, not users |
| **Everything is explainable** | Every card carries trigger, baseline, current value, window, source, confidence |
| **LLM is presentation-only** | Deterministic templates are the fallback |
| **Stale data never triggers events** | Freshness stored per snapshot and shown in UI |

---

## 4. Architecture

### High-Level Architecture

```
Browser → Next.js (App Router, TanStack Query, lightweight-charts)
              │ REST / SSE
              ▼
          FastAPI
            ├── Auth Service (argon2 + JWT httpOnly cookie)
            ├── Watchlist Service (ownership-checked CRUD)
            ├── Snapshot Service (normalize + persist provider data)
            ├── Change Detection (pure feature/threshold engine)
            ├── Attention Scoring (weighted, confidence-adjusted, explainable)
            └── Explanation Service (deterministic templates; optional LLM rewrite)
                 ▼
         PostgreSQL + Redis        Background Pipeline (in-process asyncio loop)
                                           ▼
                                 MarketDataProvider Adapter (mock | finnhub)
```

### Why This Architecture?

| Decision | Reason |
|----------|--------|
| **FastAPI for backend** | Async support, automatic OpenAPI docs, Pydantic validation, high performance |
| **Next.js App Router** | React Server Components, streaming, modern routing |
| **Separate provider layer** | Swap vendors without changing business logic |
| **In-process pipeline (MVP)** | Simple, no extra infrastructure; upgrade to Celery later |
| **PostgreSQL** | ACID compliance, JSON support, reliable for financial data |
| **Redis** | Caching, session store, future queue backend |

---

## 5. Technology Stack

### Backend (Python 3.9+)
| Technology | Version | Purpose |
|-----------|---------|---------|

---

## 6. Key Components & Why They Exist

### 6.1 Auth Service (`app/services/auth_service.py`)
**What it does**: User registration, login, JWT token management

**Why it exists**:
- Secure authentication is foundational
- Uses **argon2** (memory-hard password hashing) to resist brute-force attacks
- JWT tokens in **httpOnly cookies** prevent XSS token theft
- Rate limiting on login (10 attempts per 5 minutes)

### 6.2 Watchlist Service (`app/services/watchlist_service.py`)
**What it does**: CRUD operations for watchlists and symbols

**Why it exists**:
- Users need to organize stocks into named watchlists
- **Ownership checks everywhere** — any watchlist/event a user doesn't own returns 404 (not 403) to avoid leaking existence
- Symbol validation against provider (422 on unknown, 409 on duplicate)

### 6.3 Snapshot Service (`app/services/ingest.py`)
**What it does**: Normalizes and persists provider data

**Why it exists**:
- Raw provider data is never shown directly
- Each snapshot stores: provider name, source timestamp, ingestion time, market status, data quality
- **Conflicting-provider guard**: Never silently overwrites another provider's value
- **Freshness classification**: fresh (<5min), delayed (5-30min), stale (>30min), unknown

### 6.4 Change Detection (`app/services/change_detection.py`)
**What it does**: Pure functions that compute features and detect events

**Why it exists**:
- Separates "what happened" from "how important it is"
- **Pure functions** = testable, predictable, no side effects
- Detects: price moves, unusual volume, volatility spikes, MA breaks, gaps, relative moves

### 6.5 Attention Scoring (`app/services/attention.py`)
**What it does**: Calculates importance scores for detected events

**Why it exists**:
- Not all changes are equally important
- **Transparent scoring**: Users see exactly why something got its score
- **Confidence-adjusted**: Lower confidence = lower final score
- **Corroboration matters**: Events with ≥2 signal categories are never "background"

### 6.6 Explanation Service (`app/services/explanation.py`)
**What it does**: Generates human-readable explanations for events

**Why it exists**:
- Numbers alone don't tell the story
- **Deterministic templates first**: Always works, no API dependency
- **Optional LLM rewrite**: Only rewrites verified facts, never invents causes
- Guardrails reject advice-like content from LLM

### 6.7 Feed Service (`app/services/feed_service.py`)
**What it does**: Builds the personalized change brief

**Why it exists**:
- Combines all data into a user-friendly format
- **Visit-aware**: Only shows changes since last visit
- **User state tracking**: seen/reviewed/dismissed/saved
- Generates the change brief summary text

---

## 8. Scoring System

### Attention Score Formula

```
attention_score = Σ(weighted components)
final_score = attention_score × data_confidence
```

### Component Weights

| Component | Weight | Description |
|-----------|--------|-------------|
| **Price** | 25% | Absolute or statistical price movement |
| **Corporate Event** | 25% | Earnings, guidance, M&A, etc. |
| **News** | 15% | Scored company news |
| **Volume** | 15% | Unusual volume detection |
| **Relative Performance** | 10% | Benchmark-relative movement |
| **Volatility** | 10% | Volatility expansion |
| **Recency Bonus** | +0-10 | Decays over 24 hours |
| **Personal Preference** | -15 to +10 | User priority tags |

### Severity Bands

| Score | Severity | Action |
|-------|----------|--------|
| **80-100** | 🔴 Investigate | Immediate attention |
| **60-79** | 🟠 Review | Worth looking at |
| **35-59** | 🟡 Notable | Background noise filtered |
| **0-34** | ⚪ Background | Suppressed from feed |

### Data Confidence

```python
confidence = freshness_factor × volume_factor × history_depth_factor
```

| Factor | Values |
|--------|--------|
| **Freshness** | fresh=1.0, delayed=0.7, stale=0.4, unknown=0.3 |
| **Volume** | has_volume=1.0, no_volume=0.8 |
| **History** | >100 days=1.0, 30-100=0.85, <30=0.6 |

---

## 9. Change Detection

---

## 11. Explanation Service

### Deterministic Templates (Primary)

```python
def explain_event(symbol, change_since_visit, volume_ratio, relative_return, event_type):
    # Builds explanation from verified facts only
    # Example: "NVDA is up 5.8% since your last visit. Trading volume is 2.3x its recent average."
```

### Optional LLM Rewrite (Secondary)

**Guardrails**:
- Only receives **structured facts**, not raw data
- Must return **JSON format** with summary, key_facts, risk_note
- **Forbidden words**: "buy", "sell", "hold" with "advice"
- **Fallback**: Deterministic template if LLM fails or returns invalid

**Why LLM is optional**:
- App works fully with `LLM_API_KEY` empty
- Deterministic templates are predictable and testable
- LLM only polishes presentation, never invents causes

---

## 12. Provider Abstraction

### MarketDataProvider Protocol

```python
class MarketDataProvider(Protocol):
    async def get_quote(self, symbol: str) -> Quote: ...
    async def get_ohlcv(self, symbol: str, interval: str, lookback_days: int) -> list[Candle]: ...
    async def get_company_profile(self, symbol: str) -> CompanyProfile: ...
    async def get_corporate_events(self, symbol: str) -> list[CorporateEvent]: ...
    async def get_news(self, symbol: str, since: datetime) -> list[NewsArticle]: ...
    async def search_symbol(self, query: str) -> list[CompanyProfile]: ...
```

### Implemented Providers

| Provider | Purpose |
|----------|---------|
| **MockMarketDataProvider** | Deterministic simulator for development/demo |
| **FinnhubProvider** | Real market data (requires API key) |

### Why Abstraction?

- **Frontend and services never import a vendor SDK**
- Swap providers with one env var: `MARKET_DATA_PROVIDER=finnhub`
- Mock provider enables development without API keys
- Testable: Mock provider has `apply_shock()` and `add_corporate_event()` for demos

---

## 13. Database Design

### Entity Relationship

```

---

## 14. API Design

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Create account, argon2 hash |
| POST | `/api/auth/login` | Rate limited (10/5min) |
| POST | `/api/auth/logout` | Clear cookie |
| GET | `/api/auth/me` | Current user + last visit |

### Watchlists
| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/api/watchlists` | List/create watchlists |
| PATCH/DELETE | `/api/watchlists/{id}` | Update/delete watchlist |
| GET/POST | `/api/watchlists/{id}/symbols` | List/add symbols |
| DELETE | `/api/watchlists/{id}/symbols/{symbol}` | Remove symbol |
| PATCH | `/api/watchlists/{id}/symbols/reorder` | Reorder symbols |

### Market Data
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/market/{symbol}/latest` | Quote + freshness |
| GET | `/api/market/{symbol}/history` | Snapshot history |
| GET | `/api/market/{symbol}/events` | Event timeline |
| POST | `/api/market/{symbol}/refresh` | Manual refresh |
| POST | `/api/market/refresh-watchlist/{id}` | Refresh all symbols |

### Attention Feed
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/attention-feed?watchlist_id=` | Ranked cards + summary |
| POST | `/api/events/{id}/seen` | Mark as seen |
| POST | `/api/events/{id}/reviewed` | Mark as reviewed |
| POST | `/api/events/{id}/dismiss` | Dismiss event |
| POST | `/api/events/{id}/save` | Save event |
| POST | `/api/sessions/visit` | Record visit |
| GET/PATCH | `/api/preferences` | Get/update preferences |
| GET | `/api/stream/watchlist/{id}` | SSE heartbeat |

### Feed Response Shape

```json
{
  "since": "2026-09-04T10:30:00Z",
  "change_brief": "2 meaningful change(s) since your last visit: 1 earnings event, 1 unusual price move.",
  "summary": {
    "total_symbols": 3,
    "meaningful_changes": 2,
    "stale_instruments": 0,
    "biggest_positive_move": {"symbol": "NVDA", "change_pct": 5.8},
    "biggest_negative_move": null
  },
  "cards": [{
    "symbol": "NVDA",
    "title": "NVDA moved +5.8%",
    "final_score": 25.2,
    "severity": "notable",
    "freshness": "fresh",
    "evidence": {
      "trigger": "absolute return +5.8% >= 3.0% threshold",
      "baseline": "20-session baseline",
      "current": "5.8",
      "window": "since previous snapshot",
      "source": "mock @ 2026-09-04T12:00:00Z",
      "confidence": 0.85
    }

---

## 16. Security & Privacy

### Authentication Security
- **argon2-cffi**: Memory-hard password hashing (resistant to GPU attacks)
- **JWT in httpOnly cookies**: Prevents XSS token theft
- **Rate limiting**: 10 login attempts per 5 minutes

### Authorization
- **Ownership checks everywhere**: Every watchlist/event route verifies user ownership
- **404 not 403**: Doesn't leak existence of other users' data
- **User-scoped data**: Users can only see their own events and preferences

### Data Protection
- **No trading**: System never executes trades
- **No PII in logs**: User data not logged
- **Optional LLM**: Facts sent to LLM are structured, not raw user data

---

## 17. Testing Strategy

### Test Coverage (29 tests)

| Test File | Coverage Area |
|-----------|--------------|
| `test_features.py` | Pure feature calculations |
| `test_attention.py` | Scoring system |
| `test_change_detection.py` | Event detection |
| `test_api_flow.py` | End-to-end API flow |

### Test Categories

| Category | Tests |
|----------|-------|
| **Features** | Returns, volume ratio, volatility, MA, freshness classification |
| **Scoring** | Component weights, severity bands, confidence adjustment |
| **Detection** | Price moves, volume spikes, volatility, MA breaks, gaps |
| **Auth** | Registration, login, logout, token validation |
| **Watchlists** | CRUD, ownership, symbol validation |
| **E2E** | Full demo storyline |

---

## 19. Product Decisions

### Decision 1: Deterministic Core, Optional LLM Polish
- **Change detection is pure Python math**: Predictable, testable, cheap
- **LLM only rewrites verified facts**: Output is validated, advice-like content rejected
- **App works with `LLM_API_KEY` empty**: No hard dependency

### Decision 2: Corroboration Over Raw Thresholds
- **Single trigger crossing = "background"** if nothing corroborates it
- **Two+ independent signal categories = at least "notable"**
- This is what removes noise from the feed

### Decision 3: Since-Last-Visit is a Baseline, Not a Review
- **Dashboard records visit timestamp only after successful load**
- **Marks events seen/reviewed/dismissed only via explicit actions**
- Preserves the personalization signal

### Decision 4: Mock Provider is a Feature
- **Same protocol as licensed vendor**
- **`apply_shock` / `add_corporate_event` hooks** for demo storyline
- Swapping in Finnhub is one env var

### Decision 5: Stale Data Never Lies
- **Freshness classified per snapshot** (fresh/delayed/stale/unknown with 5-minute clock-skew tolerance)
- **Stale data renders last known value with visible badge**
- **Generates no events**

### Decision 6: Deduplication is Per Symbol/Type/Day
- **Stock that gaps up and keeps climbing = one event, not five**
- Related signals ride along in card's grouped-evidence panel

### Decision 7: Ownership Checks Everywhere
- **Any watchlist or event a user doesn't own returns 404** (not 403)
- Avoids leaking existence of other users' data

### Decision 8: Deliberately Out of Scope (MVP)
- Portfolio tracking, trading, push notifications
- Multiple simultaneous providers
- Price prediction, buy/sell recommendations

---

## 20. Feature Roadmap


---

## 21. Scaling Path

### Current (MVP)
- In-process asyncio pipeline
- SQLite/PostgreSQL
- Single instance

### Future Scaling

| Layer | Current | Future |
|-------|---------|--------|
| **Pipeline** | In-process asyncio | Celery/Dramatiq beat |
| **Caching** | None | Redis shared quote cache |
| **Dedupe** | Database | Request dedupe (single-flight per symbol) |
| **Workers** | Single process | Separate event-detection workers |
| **Database** | Basic indexes | Partition per symbol, time-series storage |
| **API** | Synchronous | Async with connection pooling |

### Database Indexes
- `(symbol, captured_at)` for snapshots
- `(symbol, detected_at)` for events
- `(user_id, event_id)` for user state

---

## 22. How to Run

### Local Development (No API Key Needed)

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

### Full Stack with Docker

```bash
cp .env.example .env   # optional: set FINNHUB / LLM keys
docker compose up --build
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MARKET_DATA_PROVIDER` | `mock` | Provider: `mock` or `finnhub` |
| `MARKET_DATA_API_KEY` | (empty) | Finnhub API key |
| `LLM_API_KEY` | (empty) | OpenAI/Groq API key |
| `LLM_MODEL` | `gpt-4o-mini` | LLM model for explanations |
| `JWT_SECRET` | `dev-secret-change-me` | JWT signing secret |
| `DATABASE_URL` | SQLite | PostgreSQL connection string |
| `REDIS_URL` | (empty) | Redis connection string |
| `POLL_INTERVAL_SECONDS` | `300` | Pipeline polling interval |

---

## Summary: Why This Project Matters

### The Problem
Investors are overwhelmed by data but starved for insight. Traditional watchlists show prices, not meaning.

### Our Solution
A system that understands **what changed**, **why it matters**, and **what's new since you last looked**.

### Key Differentiators
1. **Explainable**: Every alert has evidence, not just a score
2. **Personalized**: Visit-aware, user-specific state
3. **Noise-free**: Corroboration-based filtering
4. **Transparent**: Open scoring, no black-box AI
5. **Testable**: Pure functions, deterministic core

### Technical Excellence
- Clean architecture with separated concerns
- Provider-agnostic design
- Comprehensive testing (29 tests)
- Type-safe with Pydantic and TypeScript
- Production-ready with Docker

---

**Built with**: Python, FastAPI, Next.js, PostgreSQL, Redis, Docker

**License**: [Your License]

**Author**: [Your Name]

**Repository**: [Your Repo URL]

### Now (Implemented)
1. Guided first-run onboarding
2. Empty-watchlist checklist
3. Symbol search with provider-backed suggestions
4. Multiple named watchlists
5. Rename watchlists
6. Latest quote snapshot
7. Data freshness and market-session labels
8. Manual refresh
9. Optional five-minute auto-refresh
10. Since-last-visit change brief
11. Attention score with evidence
12. Grouped corroborating signals
13. Severity tiers
14. Search and sort attention feed
15. Saved-only filter
16. Hide-reviewed filter
17. Compact feed mode
18. Mark reviewed / Dismiss / Save
19. Scored company news
20. Persisted alert thresholds
21. CSV export of filtered changes
22. Provider error and retry states

### Backlog (Priority Order)
- Popular-symbol starter packs
- Import symbols from CSV
- Drag-and-drop symbol ordering
- Price history chart
- Volume chart
- Candlestick chart
- Moving-average overlays
- Corporate-event timeline
- Earnings calendar
- Price threshold alerts
- Volume-spike alerts
- Daily email digest
- Browser notifications
- Provider fallback chain
- Postgres production profile and migrations

| **Stale Data** | Stale data never triggers events |

### Running Tests

```bash
cd apps/api
.venv/bin/python -m pytest tests/ -q
```

---

## 18. Demo Storyline

### Step-by-Step Demo

1. **Register** → Create account with email/password
2. **Add symbols** → Add AAPL, NVDA, MSFT to watchlist
3. **Press "Refresh market data"** → Establishes baseline
4. **Dashboard shows empty cards** → By design (no changes yet)
5. **Simulate changes** → `provider.apply_shock("NVDA", 5.8, 2.3)` + `provider.add_corporate_event("MSFT", "earnings_surprise", ...)`
6. **Reload dashboard** → Shows "2 meaningful changes since your last visit"
7. **Review cards** → NVDA (price+volume, explainable evidence) and MSFT (earnings)
8. **AAPL stays invisible** → Normal drift filtered out
9. **Mark reviewed** → Next visit shows only genuinely new information

### Why This Demo Works

| Element | Purpose |
|---------|---------|
| **Empty initial state** | Shows system is working, not broken |
| **Simulated shocks** | Demonstrates detection without waiting |
| **NVDA + MSFT** | Shows different event types (price vs corporate) |
| **AAPL invisible** | Proves noise filtering works |
| **Mark reviewed** | Demonstrates visit-aware personalization |

  }]
}
```

---

## 15. Frontend Architecture

### Tech Stack
- **Next.js 14 App Router**: Server components, streaming
- **TanStack Query**: Server state management, caching, refetching
- **lightweight-charts**: Financial charting (TradingView)
- **Tailwind CSS**: Utility-first styling

### Key Components

| Component | Purpose |
|-----------|---------|
| **AttentionCard** | Displays a single change event with evidence |
| **AttentionFeed** | Ranked list of attention cards |
| **ChangeExplanation** | Human-readable explanation text |
| **DataFreshnessBadge** | Visual freshness indicator |
| **AddSymbolDialog** | Symbol search and add |
| **AlertManager** | Price alert configuration |
| **ReviewControls** | Mark reviewed/dismissed/saved |
| **PriceChart** | Price history visualization |
| **EventTimeline** | Chronological event view |
| **WatchlistSwitcher** | Switch between watchlists |
| **PortfolioPanel** | Holdings overview |
| **AnalyticsStrip** | Summary statistics |

### Page Structure

```
/app
├── dashboard/          # Main attention feed
├── login/              # Authentication
├── watchlists/         # Watchlist management
├── settings/           # User preferences
├── symbols/[symbol]/   # Symbol detail page
└── page.tsx            # Landing page
```

User ──< Watchlist ──< WatchlistSymbol
 │
 ├──< UserPreferences
 ├──< UserEventState
 ├──< PriceAlert
 ├──< Holding
 └──< SymbolNote

MarketSnapshot (normalized quotes)
MarketFeature (derived features)
MarketEvent (detected events)
NewsItem (scored news)
```

### Key Tables

| Table | Purpose |
|-------|---------|
| **users** | Authentication, visit tracking |
| **watchlists** | User-organized symbol groups |
| **watchlist_symbols** | Symbols in watchlists with priority tags |
| **market_snapshots** | Normalized, timestamped quotes |
| **market_features** | Computed features (returns, ratios, MAs) |
| **market_events** | Detected events with scores and evidence |
| **user_event_state** | Per-user event state (seen/reviewed/dismissed/saved) |
| **news_items** | Scored and deduplicated news |
| **user_preferences** | Personal thresholds and settings |
| **price_alerts** | User-configured price alerts |
| **holdings** | Optional position tracking |
| **symbol_notes** | Private journal entries |

### Why Separate Tables?

- **Raw data ≠ snapshots ≠ events ≠ user state**
- Each layer is independently queryable and testable
- Historical data preserved for analysis
- User state doesn't affect event detection


### Signal Categories

| Category | Detection Method | Threshold |
|----------|-----------------|-----------|
| **Price Move** | Absolute return OR statistical (σ-based) | ≥3% OR ≥1.5σ |
| **Unusual Volume** | Volume ratio vs 20-session average | ≥2x |
| **Volatility Spike** | Current vol / 20-day average vol | ≥1.5x |
| **MA Break** | Price crosses moving average | 20/50/200-day |
| **Gap** | Open vs previous close | ≥2% |
| **Relative Move** | Stock return - benchmark return | ≥1.5 pts |

### Corroboration Rule

> **An event with ≥2 corroborating signal categories is never ranked "background"**

This is the product's definition of **meaningful change**.

### Deduplication

- **One event per symbol/type/day**
- Related signals ride along in the card's grouped-evidence panel
- Prevents alert fatigue from repeated triggers

---

## 10. User Visit Tracking

### How It Works

1. **User visits dashboard** → Page loads with current data
2. **After successful load** → `record_visit()` updates `last_visit_at`
3. **Next visit** → Feed shows only changes since previous visit
4. **Explicit actions only** → Marking reviewed/dismissed/saved requires user action

### Why This Design?

| Decision | Reason |
|----------|--------|
| **Visit recorded AFTER load** | Prevents marking as seen if page errors |
| **No auto-review on load** | Preserves personalization signal |
| **Explicit actions only** | User intent is clear and intentional |
| **Previous visit returned** | UI can show "since your last visit" timestamp |


### 6.8 Background Pipeline (`app/workers/pipeline.py`)
**What it does**: Periodically polls market data for all watchlists

**Why it exists**:
- Automates data collection
- **Fetch once per symbol, fan out to users**: Efficient, no duplicate API calls
- **In-process asyncio**: Simple for MVP, upgrade to Celery for production
- Error isolation: One bad cycle doesn't kill the worker

---

## 7. Data Flow Pipeline

### Pipeline Steps

```
Scheduler (asyncio loop)
  → Fetch jobs (provider adapter)
  → Normalize + validate + classify freshness
  → Store snapshot
  → Compute features (pure functions)
  → Detect events (thresholds + statistical triggers)
  → Score (weighted components × data confidence)
  → Deduplicate → Persist → Attention feed query
```

### Why This Pipeline?

| Step | Purpose |
|------|---------|
| **Normalize** | Provider-agnostic data format |
| **Classify freshness** | Stale data never triggers events |
| **Compute features** | Pure functions = testable |
| **Detect events** | Multi-signal corroboration |
| **Score** | Transparent, weighted importance |
| **Deduplicate** | One event per symbol/type/day |

### Polling Intervals
- **Market hours**: 5-15 minutes
- **After hours**: 30-60 minutes
- **Nightly**: Recalculation

| **FastAPI** | 0.115.6 | Web framework with async support |
| **Uvicorn** | 0.34.0 | ASGI server |
| **SQLAlchemy** | 2.0.36 | ORM with async support |
| **Pydantic** | 2.10.4 | Data validation |
| **Pydantic-Settings** | 2.7.0 | Configuration management |
| **PyJWT** | 2.10.1 | JWT token handling |
| **argon2-cffi** | 23.1.0 | Password hashing (memory-hard) |
| **httpx** | 0.28.1 | Async HTTP client |
| **pytest** | 8.3.4 | Testing framework |
| **openai** | ≥1.50.0 | Optional LLM integration |

### Frontend (Node 18+)
| Technology | Version | Purpose |
|-----------|---------|---------|
| **Next.js** | 14.2.15 | React framework with App Router |
| **React** | 18.3.1 | UI library |
| **TanStack Query** | 5.62.0 | Server state management |
| **lightweight-charts** | 4.2.0 | Financial charting |
| **Tailwind CSS** | 3.4.13 | Utility-first styling |
| **TypeScript** | 5.6.2 | Type safety |

### Infrastructure
| Technology | Purpose |
|-----------|---------|
| **PostgreSQL 16** | Primary database |
| **Redis 7** | Caching & session store |
| **Docker** | Containerization |


### Our Solution
A system that:
1. **Filters noise** using multi-signal corroboration
2. **Ranks by importance** using transparent weighted scoring
3. **Explains why** with evidence (trigger, baseline, current value, confidence)
4. **Remembers state** — knows what you've seen and reviewed
5. **Respects your time** — only shows genuinely new information
