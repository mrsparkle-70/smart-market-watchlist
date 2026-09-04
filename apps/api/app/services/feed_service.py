"""User-specific change feed + visit tracking (sections 7 & 14)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    MarketEvent,
    MarketSnapshot,
    User,
    UserEventState,
    Watchlist,
    WatchlistSymbol,
)
from app.services.watchlist_service import get_owned_watchlist


def get_previous_visit(user: User) -> datetime | None:
    return user.last_visit_at


def record_visit(db: Session, user: User) -> datetime | None:
    """Mark visit only after successful page load (section 7). Returns previous visit."""
    previous = user.last_visit_at
    user.last_visit_at = datetime.now(timezone.utc)
    db.commit()
    return previous


def set_event_state(db: Session, user: User, event_id: int, action: str) -> UserEventState:
    """Track seen/opened/reviewed/dismissed/saved — never auto-review on page load."""
    event = db.get(MarketEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    # Authorization: event must belong to a symbol in one of the user's watchlists
    owned = db.execute(
        select(WatchlistSymbol.symbol).join(Watchlist, Watchlist.id == WatchlistSymbol.watchlist_id)
        .where(Watchlist.user_id == user.id, WatchlistSymbol.symbol == event.symbol)
    ).scalar_one_or_none()
    if owned is None:
        raise HTTPException(status_code=404, detail="Event not found")

    state = db.execute(
        select(UserEventState).where(
            UserEventState.user_id == user.id, UserEventState.event_id == event_id
        )
    ).scalar_one_or_none()
    if state is None:
        state = UserEventState(user_id=user.id, event_id=event_id)
        db.add(state)
    now = datetime.now(timezone.utc)
    setattr(state, f"{action}_at", now)  # seen|reviewed|dismissed|saved
    db.commit()
    db.refresh(state)
    return state


EVENT_LABELS = {
    "price_move": "unusual price move",
    "unusual_volume": "unusual volume",
    "volatility_spike": "volatility spike",
    "ma_break": "moving-average break",
    "gap": "gap move",
    "relative_move": "benchmark-relative move",
    "earnings": "earnings event",
    "earnings_surprise": "earnings surprise",
    "guidance_change": "guidance change",
    "news_impact": "significant news",
}

# When a symbol has several events, the card's primary event is the one that best
# answers "why should I look?" — catalysts and user-driven alerts outrank technicals.
PRIMARY_PRIORITY = {
    "personal_threshold": 0, "earnings": 0, "earnings_surprise": 0, "guidance_change": 0,
    "merger_acquisition": 0, "stock_split": 0, "dividend_change": 0, "analyst_change": 0,
    "news_impact": 1, "gap": 2, "price_move": 3, "unusual_volume": 3,
    "volatility_spike": 3, "relative_move": 3, "ma_break": 4,
}


def build_attention_feed(db: Session, user: User, watchlist_id: int) -> dict:
    """The 'Your market changed' landing payload, ranked by attention score."""
    wl = get_owned_watchlist(db, user.id, watchlist_id)
    symbols = [s.symbol for s in wl.symbols]
    now = datetime.now(timezone.utc)
    since = get_previous_visit(user)

    latest_snap: dict[str, MarketSnapshot] = {}
    for sym in symbols:
        snap = db.execute(
            select(MarketSnapshot).where(MarketSnapshot.symbol == sym)
            .order_by(MarketSnapshot.captured_at.desc()).limit(1)
        ).scalar_one_or_none()
        if snap:
            latest_snap[sym] = snap

    if symbols:
        q = (
            select(MarketEvent)
            .where(
                MarketEvent.symbol.in_(symbols),
                MarketEvent.status == "open",
                # background-level noise stays out of the attention feed (section 6)
                MarketEvent.severity != "background",
            )
            .order_by(MarketEvent.final_score.desc())
        )
        if since is not None:
            q = q.where(MarketEvent.detected_at > since)
        events = list(db.execute(q).scalars())
    else:
        events = []

    # Group related events on the same symbol (noise control, section 14)
    by_symbol: dict[str, list[MarketEvent]] = {}
    for ev in events:
        by_symbol.setdefault(ev.symbol, []).append(ev)

    states = {
        s.event_id: s for s in db.execute(
            select(UserEventState).where(UserEventState.user_id == user.id)
        ).scalars()
    }
    name_by_symbol = {s.symbol: s.display_name for s in wl.symbols}

    cards = []
    for sym, evs in by_symbol.items():
        # Deterministic primary: highest score, then type priority (catalyst > technical)
        evs = sorted(evs, key=lambda e: (-e.final_score, PRIMARY_PRIORITY.get(e.event_type, 5)))
        snap = latest_snap.get(sym)
        primary = evs[0]
        change_visit = primary.evidence_json.get("features", {}).get("return_since_previous_snapshot")
        if since is None or change_visit is None:
            change_visit = None
        state = states.get(primary.id)
        cards.append({
            "id": primary.id,
            "symbol": sym,
            "company_name": name_by_symbol.get(sym, sym),
            "event_type": primary.event_type,
            "title": primary.title,
            "summary": primary.summary,
            "attention_score": primary.attention_score,
            "confidence_score": primary.confidence_score,
            "final_score": primary.final_score,
            "severity": primary.severity,
            "detected_at": primary.detected_at,
            "price": snap.price if snap else None,
            "change_since_last_visit_pct": change_visit,
            "change_since_close_pct": (
                (snap.price - snap.previous_close) / snap.previous_close * 100
                if snap and snap.previous_close else None
            ),
            "freshness": snap.data_quality if snap else "unknown",
            "evidence": {
                "trigger": primary.evidence_json.get("trigger", ""),
                "baseline": primary.evidence_json.get("baseline", ""),
                "current": str(primary.evidence_json.get("current", "")),
                "window": primary.evidence_json.get("window", ""),
                "source": primary.evidence_json.get("source", ""),
                "confidence": primary.confidence_score,
                "extra": {"related_events": [
                    {"type": e.event_type, "title": e.title, "score": e.final_score} for e in evs[1:]
                ]},
            },
            "user_state": {
                "seen_at": state.seen_at if state else None,
                "reviewed_at": state.reviewed_at if state else None,
                "dismissed_at": state.dismissed_at if state else None,
                "saved_at": state.saved_at if state else None,
            },
        })
    return _finalize_feed(db, wl, symbols, since, now, cards, latest_snap)


def _finalize_feed(db, wl, symbols, since, now, cards, latest_snap) -> dict:
    """Summary strip + top-level change brief. Cards are pre-filtered to non-background."""
    meaningful = cards
    stale = [s for s, snap in latest_snap.items() if snap.data_quality in ("stale", "unknown")]
    moves = []
    for sym, snap in latest_snap.items():
        if snap.previous_close:
            moves.append({"symbol": sym,
                          "change_pct": round((snap.price - snap.previous_close) / snap.previous_close * 100, 2)})
    moves.sort(key=lambda m: m["change_pct"])
    summary = {
        "total_symbols": len(symbols),
        "meaningful_changes": len(meaningful),
        "stale_instruments": len(stale),
        "biggest_positive_move": moves[-1] if moves and moves[-1]["change_pct"] > 0 else None,
        "biggest_negative_move": moves[0] if moves and moves[0]["change_pct"] < 0 else None,
    }

    event_counts: dict[str, int] = {}
    for c in meaningful:
        label = EVENT_LABELS.get(c["event_type"], c["event_type"])
        event_counts[label] = event_counts.get(label, 0) + 1
    if since is None:
        brief = "Baseline recorded. Your next visit will show what changed since today."
    elif not meaningful:
        brief = "Nothing meaningful changed since your last visit."
    else:
        breakdown = ", ".join(f"{n} {label}" for label, n in event_counts.items())
        brief = f"{len(meaningful)} meaningful change(s) since your last visit: {breakdown}."

    return {"since": since, "generated_at": now, "cards": cards, "summary": summary, "change_brief": brief}

