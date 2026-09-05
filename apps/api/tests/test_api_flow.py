"""Integration tests: auth, watchlists, and the full demo storyline (section 23)."""
from tests.conftest import register_and_login


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200


def test_auth_register_login_me(client):
    register_and_login(client)
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "demo@example.com"

    # duplicate registration rejected
    r = client.post("/api/auth/register", json={"email": "demo@example.com", "password": "password123"})
    assert r.status_code == 400

    # wrong password rejected
    r = client.post("/api/auth/login", json={"email": "demo@example.com", "password": "wrong-pass"})
    assert r.status_code == 401

    # unauthenticated access rejected
    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401


def test_watchlist_crud_and_symbols(client):
    register_and_login(client)
    wl = client.post("/api/watchlists", json={"name": "Tech"}).json()
    wid = wl["id"]

    assert client.post(f"/api/watchlists/{wid}/symbols", json={"symbol": "NVDA"}).status_code == 201
    assert client.post(f"/api/watchlists/{wid}/symbols", json={"symbol": "NVDA"}).status_code == 409
    assert client.post(f"/api/watchlists/{wid}/symbols", json={"symbol": "MSFT"}).status_code == 201
    assert client.delete(f"/api/watchlists/{wid}/symbols/MSFT").status_code == 204

    # user-level authorization: another user cannot touch this watchlist
    client.post("/api/auth/logout")
    register_and_login(client, email="other@example.com")
    assert client.get(f"/api/watchlists/{wid}/symbols").status_code == 404
    assert client.post(f"/api/watchlists/{wid}/symbols", json={"symbol": "AAPL"}).status_code == 404


def test_unknown_symbol_rejected(client):
    register_and_login(client)
    wid = client.post("/api/watchlists", json={"name": "T"}).json()["id"]
    r = client.post(f"/api/watchlists/{wid}/symbols", json={"symbol": "ZZZZZZ"})
    assert r.status_code == 422


def test_demo_storyline_end_to_end(client, provider):
    """Section 23: add symbols -> visit -> simulate changes -> feed -> reviewed."""
    register_and_login(client)
    wl = client.post("/api/watchlists", json={"name": "Demo"}).json()
    wid = wl["id"]
    for sym in ["AAPL", "NVDA", "MSFT"]:
        assert client.post(f"/api/watchlists/{wid}/symbols", json={"symbol": sym}).status_code == 201

    # First pipeline pass establishes the baseline
    r = client.post(f"/api/market/refresh-watchlist/{wid}")
    assert r.status_code == 200, r.text

    # First visit: baseline recorded, no meaningful changes expected
    r = client.get(f"/api/attention-feed?watchlist_id={wid}")
    assert r.status_code == 200
    feed1 = r.json()
    assert feed1["summary"]["total_symbols"] == 3
    assert feed1["change_brief"].startswith("Baseline recorded")

    # Record the visit
    visit = client.post("/api/sessions/visit")
    assert visit.status_code == 200
    assert visit.json()["previous_visit_at"] is None

    # --- Simulate market changes while the user is away ---
    provider.apply_shock("NVDA", pct=5.8, volume_multiplier=2.3)  # sharp move on unusual volume
    provider.apply_shock("AAPL", pct=0.4)                        # normal move
    provider.add_corporate_event("MSFT", "earnings_surprise", "Q3 earnings: revenue beat, guidance raised")
    r = client.post(f"/api/market/refresh-watchlist/{wid}")
    assert r.status_code == 200

    # --- User returns: the feed must surface exactly what matters ---
    feed2 = client.get(f"/api/attention-feed?watchlist_id={wid}").json()
    symbols_in_feed = {c["symbol"] for c in feed2["cards"]}
    assert "NVDA" in symbols_in_feed, feed2
    assert "MSFT" in symbols_in_feed, feed2
    assert "AAPL" not in symbols_in_feed, "normal move must not appear"
    assert "2 meaningful change" in feed2["change_brief"]

    nvda = next(c for c in feed2["cards"] if c["symbol"] == "NVDA")
    msft = next(c for c in feed2["cards"] if c["symbol"] == "MSFT")
    # both surfaced as worth attention (non-background severity)
    assert nvda["severity"] in ("notable", "review", "investigate")
    assert msft["severity"] in ("notable", "review", "investigate")
    assert nvda["change_since_last_visit_pct"] and nvda["change_since_last_visit_pct"] > 5
    # Explainability: every card carries trigger/baseline/current/source/confidence
    for card in (nvda, msft):
        ev = card["evidence"]
        assert ev["trigger"] and ev["source"] and ev["confidence"] > 0
    assert "2.3x" in nvda["summary"] or "2.2x" in nvda["summary"] or "recent average" in nvda["summary"]

    # Mark NVDA reviewed
    r = client.post(f"/api/events/{nvda['id']}/reviewed")
    assert r.status_code == 200 and r.json()["reviewed_at"]

    # Record this visit, then reload: NVDA must be gone (dedupe + since-visit window)
    client.post("/api/sessions/visit")
    feed3 = client.get(f"/api/attention-feed?watchlist_id={wid}").json()
    assert feed3["cards"] == []
    assert "Nothing meaningful changed" in feed3["change_brief"]


def test_scenario_library(client, provider):
    """The demo scenario library drives many more detection cases end-to-end."""
    register_and_login(client)
    wid = client.post("/api/watchlists", json={"name": "S"}).json()["id"]
    for sym in ["AAPL", "NVDA", "MSFT", "TSLA"]:
        client.post(f"/api/watchlists/{wid}/symbols", json={"symbol": sym})
    client.post("/api/sessions/visit")

    scenarios = client.get("/api/demo/scenarios").json()
    assert len(scenarios) >= 9

    # Sector rotation: NVDA +3% while SPY -1% -> relative_move (absolute move below bar)
    r = client.post("/api/demo/simulate", json={"scenario": "sector_rotation"})
    assert r.status_code == 200
    types = {c["event_type"] for c in client.get(f"/api/attention-feed?watchlist_id={wid}").json()["cards"]}
    assert "relative_move" in types, types

    # News burst -> scored news_impact events
    client.post("/api/sessions/visit")
    client.post("/api/demo/simulate", json={"scenario": "news_burst"})
    cards = client.get(f"/api/attention-feed?watchlist_id={wid}").json()["cards"]
    news_cards = [c for c in cards if c["event_type"] == "news_impact"]
    assert news_cards and all(c["evidence"]["confidence"] > 0 for c in news_cards)

    # Flash crash -> price move + unusual volume + volatility for TSLA
    client.post("/api/sessions/visit")
    client.post("/api/demo/simulate", json={"scenario": "flash_crash"})
    cards = client.get(f"/api/attention-feed?watchlist_id={wid}").json()["cards"]
    assert any(c["symbol"] == "TSLA" for c in cards)

    # Trend break -> ma_break detection
    client.post("/api/sessions/visit")
    client.post("/api/demo/simulate", json={"scenario": "trend_break"})
    cards = client.get(f"/api/attention-feed?watchlist_id={wid}").json()["cards"]
    assert any(c["event_type"] == "ma_break" for c in cards)

    # Personal alert: AAPL tagged high_priority moves +2% (below the standard bar)
    client.post("/api/sessions/visit")
    client.post("/api/demo/simulate", json={"scenario": "personal_alert"})
    cards = client.get(f"/api/attention-feed?watchlist_id={wid}").json()["cards"]
    assert any(c["event_type"] == "personal_threshold" for c in cards)

    # Quiet day -> nothing meaningful
    client.post("/api/sessions/visit")
    client.post("/api/demo/simulate", json={"scenario": "quiet_day"})
    feed = client.get(f"/api/attention-feed?watchlist_id={wid}").json()
    assert feed["cards"] == []


def test_stale_data_produces_no_events(client, provider):
    """Section 11: stale data shows last known value but never triggers events."""
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch

    from app.providers.base import Quote

    register_and_login(client)
    wid = client.post("/api/watchlists", json={"name": "D"}).json()["id"]
    client.post(f"/api/watchlists/{wid}/symbols", json={"symbol": "TSLA"})
    client.post(f"/api/market/refresh-watchlist/{wid}")
    client.post("/api/sessions/visit")

    provider.apply_shock("TSLA", pct=6.0, volume_multiplier=3.0)
    old_ts = datetime.now(timezone.utc) - timedelta(hours=2)

    original_get_quote = provider.get_quote

    async def stale_quote(symbol):
        q = await original_get_quote(symbol)
        return Quote(symbol=q.symbol, price=q.price, previous_close=q.previous_close,
                     open_price=q.open_price, high_price=q.high_price, low_price=q.low_price,
                     volume=q.volume, market_status="open", source_timestamp=old_ts,
                     provider=q.provider)

    with patch.object(provider, "get_quote", side_effect=stale_quote):
        r = client.post(f"/api/market/refresh-watchlist/{wid}")
    assert r.status_code == 200

    feed = client.get(f"/api/attention-feed?watchlist_id={wid}").json()
    assert feed["cards"] == []
    latest = client.get("/api/market/TSLA/latest").json()
    assert latest["freshness"] == "stale"  # visible stale indicator


def test_portfolio_alerts_and_notes_are_persisted(client, provider):
    register_and_login(client)
    wid = client.post("/api/watchlists", json={"name": "Research"}).json()["id"]
    assert client.post(f"/api/watchlists/{wid}/symbols", json={"symbol": "NVDA"}).status_code == 201
    assert client.post(f"/api/market/refresh-watchlist/{wid}").status_code == 200
    analytics = client.get("/api/market/NVDA/analytics?days=90")
    assert analytics.status_code == 200
    assert analytics.json()["observations"] == 1

    note = client.put("/api/market/NVDA/note", json={"body": "Watch gross margin and guidance."})
    assert note.status_code == 200
    assert client.get("/api/market/NVDA/note").json()["body"] == "Watch gross margin and guidance."

    holding = client.put("/api/portfolio/NVDA", json={"symbol": "NVDA", "quantity": 4, "average_cost": 100})
    assert holding.status_code == 200
    assert holding.json()["invested_value"] == 400
    assert holding.json()["market_value"] is not None

    alert = client.post("/api/market/NVDA/alerts", json={"condition": "price_above", "threshold": 1})
    assert alert.status_code == 201
    assert len(client.get("/api/market/NVDA/alerts").json()) == 1
    provider.apply_shock("NVDA", pct=5)
    assert client.post(f"/api/market/refresh-watchlist/{wid}").status_code == 200
    triggered = client.get("/api/market/NVDA/alerts").json()[0]
    assert triggered["last_triggered_at"] is not None
    # Triggered-alerts feed surfaces fired alerts (fix for review item #3).
    feed = client.get("/api/market/alerts/triggered").json()
    assert any(a["id"] == alert.json()["id"] and a["last_triggered_at"] is not None for a in feed)
    assert client.delete("/api/portfolio/NVDA").status_code == 204
    # A different user must not see this user's triggered alerts.
    client.post("/api/auth/logout")
    from tests.conftest import register_and_login as rl
    rl(client, email="other@example.com")
    assert client.get("/api/market/alerts/triggered").json() == []


def test_market_endpoints_require_watchlist_membership(client, provider):
    """Section 16: every per-symbol route must verify the user watches the symbol."""
    register_and_login(client)
    # NVDA is not on this user's watchlist.
    for path in (
        "/api/market/NVDA/history",
        "/api/market/NVDA/analytics",
        "/api/market/NVDA/events",
        "/api/market/NVDA/news",
    ):
        assert client.get(path).status_code == 404, f"{path} leaked data"


def test_jwt_secret_insecure_default_blocked_in_production(monkeypatch):
    """Section 16: do not allow production to start with a public JWT secret."""
    from app.core.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "change-me-in-production")
    try:
        try:
            get_settings()
        except RuntimeError as exc:
            assert "JWT_SECRET" in str(exc)
        else:
            raise AssertionError("expected RuntimeError for insecure JWT_SECRET in production")
    finally:
        get_settings.cache_clear()
