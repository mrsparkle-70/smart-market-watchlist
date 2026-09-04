# Product Decisions

1. **Deterministic core, optional LLM polish.** Change detection is pure Python math —
   predictable, testable, cheap. The LLM (Groq free tier, OpenAI-compatible) may only
   rewrite verified structured facts; output is validated and advice-like content is
   rejected. The app works fully with `LLM_API_KEY` empty.

2. **Corroboration over raw thresholds.** A single trigger crossing is "background" if
   nothing corroborates it. Two or more independent signal categories (price, volume,
   volatility, relative performance) or a major corporate event guarantee at least
   "notable". This is what removes noise from the feed.

3. **Since-last-visit is a baseline, not a review.** The dashboard records the visit
   timestamp only after successful load, and marks events seen/reviewed/dismissed only
   via explicit actions. This preserves the personalization signal.

4. **Mock provider is a feature.** The simulator (`MockMarketDataProvider`) implements the
   same protocol as a licensed vendor, with `apply_shock` / `add_corporate_event` hooks
   for the demo storyline. Swapping in Finnhub is one env var.

5. **Stale data never lies.** Freshness is classified per snapshot (fresh/delayed/stale/
   unknown with 5-minute clock-skew tolerance); stale data renders the last known value
   with a visible badge and generates no events.

6. **Deduplication is per symbol/type/day.** A stock that gaps up and keeps climbing is
   one event, not five. Related signals ride along in the card's grouped-evidence panel.

7. **Ownership checks everywhere.** Any watchlist or event a user doesn't own returns
   404 (not 403) to avoid leaking existence.

8. **Deliberately out of scope (MVP):** portfolio tracking, trading, push notifications,
   multiple simultaneous providers, price prediction, buy/sell recommendations.
