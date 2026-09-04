"""Authentication service: register/login/logout/me with rate limiting (section 9)."""
from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models import User, UserPreferences

# Simple in-memory rate limiter (Redis in production, see docs/architecture.md)
_login_attempts: dict[str, list[float]] = {}
_MAX_ATTEMPTS = 10
_WINDOW_SECONDS = 300


class AuthError(Exception):
    pass


def _rate_limited(key: str) -> bool:
    now = time.time()
    attempts = [t for t in _login_attempts.get(key, []) if now - t < _WINDOW_SECONDS]
    _login_attempts[key] = attempts
    return len(attempts) >= _MAX_ATTEMPTS


def _record_attempt(key: str) -> None:
    _login_attempts.setdefault(key, []).append(time.time())


def register(db: Session, email: str, password: str) -> User:
    email = email.strip().lower()
    if _rate_limited(f"register:{email}"):
        raise AuthError("Too many attempts. Try again later.")
    _record_attempt(f"register:{email}")
    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        raise AuthError("An account with this email already exists.")
    user = User(email=email, password_hash=hash_password(password))
    user.preferences = UserPreferences(user_id=user.id)  # type: ignore[arg-type]
    db.add(user)
    db.commit()
    db.refresh(user)
    # Every user starts with a default watchlist
    from app.models import Watchlist

    db.add(Watchlist(user_id=user.id, name="My Watchlist", is_default=True))
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> tuple[User, str]:
    email = email.strip().lower()
    if _rate_limited(f"login:{email}"):
        raise AuthError("Too many attempts. Try again later.")
    _record_attempt(f"login:{email}")
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password.")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return user, create_access_token(str(user.id))


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)
