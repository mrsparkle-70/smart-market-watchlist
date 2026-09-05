"""Feature #2: Alembic migration integrity tests.

Verifies the checked-in migration history builds the same schema as the
SQLAlchemy models, on a throwaway SQLite database.
"""
from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect


def _alembic_cfg(tmp_path) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_path}/mig.db")
    return cfg


def test_upgrade_head_matches_models(tmp_path):
    """`alembic upgrade head` on a fresh DB must equal Base.metadata."""
    cfg = _alembic_cfg(tmp_path)
    command.upgrade(cfg, "head")

    from sqlalchemy import create_engine

    from app.core.database import Base
    from app import models  # noqa: F401

    engine = create_engine(f"sqlite:///{tmp_path}/mig.db")
    insp = inspect(engine)
    model_tables = set(Base.metadata.tables)
    db_tables = set(insp.get_table_names()) - {"alembic_version"}
    assert model_tables == db_tables, (
        f"Migration drift: missing={model_tables - db_tables}, extra={db_tables - model_tables}"
    )

    # Column spot check on a core table (names + key columns exist).
    users_cols = {c["name"] for c in insp.get_columns("users")}
    assert {"id", "email", "password_hash", "created_at"} <= users_cols
    engine.dispose()


def test_downgrade_reverses_cleanly(tmp_path):
    cfg = _alembic_cfg(tmp_path)
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    from sqlalchemy import create_engine, inspect

    engine = create_engine(f"sqlite:///{tmp_path}/mig.db")
    tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
    assert not tables, f"Tables left after downgrade: {tables}"
    engine.dispose()
