"""Programmatic Alembic runner (feature #2).

The API calls `upgrade_to_head()` from `init_db()` when running on Postgres so
a deployed container always brings its schema up to date before serving.

`ALEMBIC_DATABASE_URL` overrides the target URL (used by tests); otherwise the
app's `DATABASE_URL` is used.
"""
from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config

_API_DIR = Path(__file__).resolve().parent.parent  # apps/api/


def _alembic_config() -> Config:
    cfg = Config(str(_API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_API_DIR / "alembic"))
    url = os.environ.get("ALEMBIC_DATABASE_URL") or ""
    if url:
        cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def upgrade_to_head() -> None:
    """Apply all pending migrations (no-op when already at head)."""
    command.upgrade(_alembic_config(), "head")
