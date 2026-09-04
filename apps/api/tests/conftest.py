"""Test fixtures: isolated sqlite DB, mock provider, TestClient."""
from __future__ import annotations

import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_watchlist.db")
os.environ.setdefault("PIPELINE_ENABLED", "false")
os.environ.setdefault("JWT_SECRET", "test-secret")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.providers.mock import MockMarketDataProvider  # noqa: E402
from app.providers import get_provider  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def provider():
    """Install a fresh mock provider as the app-wide singleton so demo shocks apply."""
    import app.providers as providers_pkg

    p = MockMarketDataProvider(seed=7)
    providers_pkg._provider_instance = p
    yield p
    providers_pkg._provider_instance = None


@pytest.fixture
def client(provider):
    with TestClient(app) as c:
        yield c



def register_and_login(client, email="demo@example.com", password="password123"):
    r = client.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.json()
