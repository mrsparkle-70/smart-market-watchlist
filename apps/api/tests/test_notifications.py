"""Tests for feature #1: real alert delivery (email + web push)."""
from __future__ import annotations

from datetime import datetime, time, timezone

from app.services import notify as N


def _setup_user_with_symbol(client, email="alerts@example.com", symbol="NVDA"):
    register_and_login(client, email=email)
    # auth_service.register() already created a default watchlist; use it.
    wid = client.get("/api/watchlists").json()[0]["id"]
    r = client.post(f"/api/watchlists/{wid}/symbols", json={"symbol": symbol})
    assert r.status_code == 201, r.text
    return wid


def test_email_channel_added_unverified(client, provider):
    _setup_user_with_symbol(client)
    r = client.post("/api/notifications/channels/email", json={"email": "me@example.com"})
    assert r.status_code == 201
    ch = r.json()
    assert ch["kind"] == "email"
    assert ch["target"] == "me@example.com"
    assert ch["enabled"] is True
    assert ch["verified"] is False
    assert any(c["target"] == "me@example.com" for c in client.get("/api/notifications/channels").json())


def test_email_channel_duplicate_is_idempotent(client, provider):
    _setup_user_with_symbol(client)
    client.post("/api/notifications/channels/email", json={"email": "me@example.com"})
    r2 = client.post("/api/notifications/channels/email", json={"email": "me@example.com"})
    assert r2.status_code == 201
    channels = client.get("/api/notifications/channels").json()
    assert len([c for c in channels if c["target"] == "me@example.com"]) == 1


def test_webpush_channel_requires_keys(client, provider):
    _setup_user_with_symbol(client)
    r = client.post("/api/notifications/channels/webpush",
                    json={"endpoint": "https://fcm.googleapis.com/x", "keys": {}})
    assert r.status_code == 422


def test_webpush_channel_accepted_and_verified(client, provider):
    _setup_user_with_symbol(client)
    r = client.post("/api/notifications/channels/webpush", json={
        "endpoint": "https://fcm.googleapis.com/x",
        "keys": {"p256dh": "abc", "auth": "def"},
    })
    assert r.status_code == 201
    assert r.json()["verified"] is True


def test_toggle_and_remove_channel(client, provider):
    _setup_user_with_symbol(client)
    ch = client.post("/api/notifications/channels/webpush", json={
        "endpoint": "https://fcm.googleapis.com/x", "keys": {"p256dh": "a", "auth": "b"},
    }).json()
    cid = ch["id"]
    r = client.patch(f"/api/notifications/channels/{cid}", json={"enabled": False})
    assert r.status_code == 200 and r.json()["enabled"] is False
    assert client.delete(f"/api/notifications/channels/{cid}").status_code == 204
    assert all(c["id"] != cid for c in client.get("/api/notifications/channels").json())


def test_remove_other_users_channel_is_404(client, provider):
    _setup_user_with_symbol(client, email="a@example.com")
    ch = client.post("/api/notifications/channels/webpush", json={
        "endpoint": "https://fcm.googleapis.com/a", "keys": {"p256dh": "a", "auth": "b"},
    }).json()
    cid = ch["id"]
    client.post("/api/auth/logout")
    register_and_login(client, email="b@example.com")
    assert client.delete(f"/api/notifications/channels/{cid}").status_code == 404


def test_alert_trigger_creates_inapp_log_when_no_channels(client, provider):
    wid = _setup_user_with_symbol(client, symbol="NVDA")
    client.post(f"/api/market/refresh-watchlist/{wid}")
    client.post(f"/api/market/NVDA/alerts", json={"condition": "price_above", "threshold": 1})
    provider.apply_shock("NVDA", pct=10)
    client.post(f"/api/market/refresh-watchlist/{wid}")
    log = client.get("/api/notifications/log").json()
    assert any(l["kind"] == "inapp" and "NVDA" in l["title"] for l in log)


def test_alert_trigger_fans_out_to_webpush_channel(client, provider):
    wid = _setup_user_with_symbol(client, symbol="NVDA")
    client.post("/api/notifications/channels/webpush", json={
        "endpoint": "https://fcm.googleapis.com/push", "keys": {"p256dh": "k", "auth": "v"},
    })
    client.post(f"/api/market/refresh-watchlist/{wid}")
    client.post(f"/api/market/NVDA/alerts", json={"condition": "price_above", "threshold": 1})
    provider.apply_shock("NVDA", pct=10)
    client.post(f"/api/market/refresh-watchlist/{wid}")
    log = client.get("/api/notifications/log").json()
    webpush_logs = [l for l in log if l["kind"] == "webpush"]
    assert any(l["status"] in ("queued", "failed") for l in webpush_logs)


def test_send_test_returns_409_when_vapid_unconfigured(client, provider):
    _setup_user_with_symbol(client, symbol="NVDA")
    ch = client.post("/api/notifications/channels/webpush", json={
        "endpoint": "https://fcm.googleapis.com/x", "keys": {"p256dh": "a", "auth": "b"},
    }).json()
    cid = ch["id"]
    r = client.post(f"/api/notifications/channels/{cid}/test")
    # VAPID is not configured in the test env, so the test endpoint refuses.
    assert r.status_code == 409


def test_preferences_round_trip(client, provider):
    _setup_user_with_symbol(client)
    r = client.get("/api/notifications/preferences")
    assert r.status_code == 200
    assert r.json()["notification_enabled"] is True
    r = client.patch("/api/notifications/preferences", json={
        "notification_enabled": False, "daily_digest": True,
        "quiet_hours_start": "22:00", "quiet_hours_end": "07:00",
    })
    assert r.status_code == 200
    out = r.json()
    assert out["notification_enabled"] is False
    assert out["daily_digest"] is True
    assert out["quiet_hours_start"].startswith("22:00")
    assert out["quiet_hours_end"].startswith("07:00")


def test_preferences_invalid_time_format(client, provider):
    _setup_user_with_symbol(client)
    r = client.patch("/api/notifications/preferences", json={"quiet_hours_start": "25:99"})
    assert r.status_code == 422


def test_log_mark_read(client, provider):
    wid = _setup_user_with_symbol(client, symbol="NVDA")
    client.post(f"/api/market/refresh-watchlist/{wid}")
    client.post(f"/api/market/NVDA/alerts", json={"condition": "price_above", "threshold": 1})
    provider.apply_shock("NVDA", pct=10)
    client.post(f"/api/market/refresh-watchlist/{wid}")
    log = client.get("/api/notifications/log").json()
    assert log, "expected at least one log row"
    lid = log[0]["id"]
    assert client.post(f"/api/notifications/log/{lid}/read").status_code == 204
    after = client.get("/api/notifications/log").json()
    assert any(l["id"] == lid and l["read_at"] is not None for l in after)


def test_quiet_hours_helper_blocks_during_window():
    prefs = type("P", (), {
        "quiet_hours_start": time(22, 0),
        "quiet_hours_end": time(7, 0),
        "daily_digest": False,
    })()
    at_23 = datetime(2024, 1, 1, 23, 0, tzinfo=timezone.utc)
    at_03 = datetime(2024, 1, 1, 3, 0, tzinfo=timezone.utc)
    at_12 = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert N._in_quiet_hours(at_23, prefs) is True
    assert N._in_quiet_hours(at_03, prefs) is True
    assert N._in_quiet_hours(at_12, prefs) is False


def test_alert_blocked_when_notification_disabled(client, provider):
    wid = _setup_user_with_symbol(client, symbol="NVDA")
    client.patch("/api/notifications/preferences", json={"notification_enabled": False})
    client.post(f"/api/market/refresh-watchlist/{wid}")
    client.post(f"/api/market/NVDA/alerts", json={"condition": "price_above", "threshold": 1})
    provider.apply_shock("NVDA", pct=10)
    client.post(f"/api/market/refresh-watchlist/{wid}")
    assert client.get("/api/notifications/log").json() == []


def register_and_login(client, email="demo@example.com", password="password123"):
    from tests.conftest import register_and_login as _rl
    return _rl(client, email=email, password=password)

