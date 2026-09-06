# API Reference

Base URL: `http://localhost:8000`. Interactive docs: `/api/docs`.
Auth via HTTP-only cookie (`smw_access_token`) or `Authorization: Bearer <jwt>`.
Every watchlist/event route verifies user ownership.

## Auth
| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/api/auth/register` | `{email, password}` | argon2 hash, creates default watchlist |
| POST | `/api/auth/login` | `{email, password}` | rate limited (10 / 5 min) |
| POST | `/api/auth/logout` | — | clears cookie |
| GET | `/api/auth/me` | — | current user + last visit |

## Watchlists & symbols
| Method | Path |
|---|---|
| GET/POST | `/api/watchlists` |
| PATCH/DELETE | `/api/watchlists/{id}` |
| GET/POST | `/api/watchlists/{id}/symbols` |
| DELETE | `/api/watchlists/{id}/symbols/{symbol}` |
| PATCH | `/api/watchlists/{id}/symbols/reorder` |

Symbol addition validates the ticker against the provider (422 on unknown, 409 on duplicate).

## Market data
| Method | Path | Notes |
|---|---|---|
| GET | `/api/market/{symbol}/latest` | quote + freshness + data quality |
| GET | `/api/market/{symbol}/history?limit=1000` | chart candles (OHLCV points), most-recent window oldest→newest, same-second snapshots deduped |
| GET | `/api/market/{symbol}/relative?benchmark=SPY&days=90` | daily cumulative % return vs benchmark, rebased to 0% on the first common day (one close per UTC day; default benchmark `SPY`, 5–730 days) |
| GET | `/api/market/{symbol}/analytics` | rolling analytics (most recent window) |
| GET | `/api/market/{symbol}/events` | full detected-event timeline |
| POST | `/api/market/{symbol}/refresh` | run one pipeline pass for a symbol |
| POST | `/api/market/refresh-watchlist/{id}` | pipeline pass for all symbols |

## Attention feed & user state
| Method | Path | Notes |
|---|---|---|
| GET | `/api/attention-feed?watchlist_id=` | ranked cards + summary + change brief |
| POST | `/api/events/{id}/seen` / `reviewed` / `dismiss` / `save` | explicit user actions only |
| POST | `/api/sessions/visit` | call AFTER page load; returns previous visit timestamp |
| GET/PATCH | `/api/preferences` | personal thresholds |
| GET | `/api/stream/watchlist/{id}` | Server-Sent Events heartbeat channel |

## Feed response shape
```json
{
  "since": "2026-09-04T10:30:00Z",
  "change_brief": "2 meaningful change(s) since your last visit: 1 earnings event, 1 unusual price move.",
  "summary": { "total_symbols": 3, "meaningful_changes": 2, "stale_instruments": 0,
                "biggest_positive_move": {"symbol": "NVDA", "change_pct": 5.8}, ... },
  "cards": [{
    "symbol": "NVDA", "title": "NVDA moved +5.8%", "final_score": 25.2,
    "severity": "notable", "freshness": "fresh",
    "evidence": { "trigger": "...", "baseline": "...", "current": "...",
                   "window": "...", "source": "mock @ ...", "confidence": 0.85 }
  }]
}
```
