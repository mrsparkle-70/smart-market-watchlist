"""Shared FastAPI dependencies: DB session, authenticated user, provider."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User
from app.providers import get_provider
from app.providers.base import MarketDataProvider

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Accepts HTTP-only cookie (browser) or Authorization: Bearer (tests/clients)."""
    token = request.cookies.get("smw_access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        scheme, param = get_authorization_scheme_param(auth)
        if scheme.lower() == "bearer":
            token = param
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    subject = decode_access_token(token)
    if subject is None or not subject.isdigit():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.get(User, int(subject))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_market_provider() -> MarketDataProvider:
    return get_provider()
