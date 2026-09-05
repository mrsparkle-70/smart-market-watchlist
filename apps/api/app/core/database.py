"""Database engine and session management (SQLAlchemy 2.0, sync)."""
from __future__ import annotations
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

connect_args = {}
engine_kwargs: dict = {"future": True, "pool_pre_ping": True}
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite permits one writer at a time. A busy timeout prevents transient
    # request/worker overlap from surfacing as "database is locked" errors.
    connect_args = {"check_same_thread": False, "timeout": 30}
elif settings.DATABASE_URL.startswith("postgres"):
    # Postgres runs on QueuePool defaults; pre_ping evicts connections reaped
    # by the server between requests, and explicit pool sizing avoids
    # surprises under the notification/pipeline workers.
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, **engine_kwargs)

if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _configure_sqlite(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create/upgrade the schema.

    Postgres (production): run Alembic migrations to `head` so the deployed
    schema always matches the checked-in migration history.

    SQLite (dev/tests): create_all for convenience — see docs/architecture.md.
    """
    from app import models  # noqa: F401  (register models)

    if settings.DATABASE_URL.startswith("postgres"):
        from app.core.migrations import upgrade_to_head

        upgrade_to_head()
        return
    Base.metadata.create_all(bind=engine)
