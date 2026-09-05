"""Database backup CLI (feature #2).

Usage (from apps/api/):
    .venv/bin/python -m app.tools.backup                 # backup now
    .venv/bin/python -m app.tools.backup --list          # list backups
    .venv/bin/python -m app.tools.backup --keep 14       # keep last 14

Behavior by DATABASE_URL:
  - postgresql*  -> `pg_dump -Fc` custom-format archive (pg_restore-ready)
  - sqlite*      -> online backup via SQLite's backup API (safe while the
                    API is running; copies through the pager, not the file)

Backups land in BACKUP_DIR (default `<repo>/backups/`), named
`smw-<timestamp>.dump|db`. Old backups beyond --keep are deleted.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine

from app.core.config import settings

_REPO_ROOT = Path(__file__).resolve().parents[3]  # repo/
_DEFAULT_BACKUP_DIR = _REPO_ROOT / "backups"

_STAMP_FMT = "%Y%m%d-%H%M%S"
_SAFE_URL_RE = re.compile(r"^[a-z]+(\+[a-z0-9]+)?://" )


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime(_STAMP_FMT)


def _backup_dir() -> Path:
    return Path(os.environ.get("BACKUP_DIR", str(_DEFAULT_BACKUP_DIR)))


def backup_postgres(url: str, dest: Path) -> None:
    """pg_dump custom-format archive (compressed, restore with pg_restore)."""
    cmd = ["pg_dump", "--no-owner", "--no-privileges", "--format=custom", "--file", str(dest)]
    # Parse user/password out of the URL so we never put them in argv listings.
    cmd += [_pq_url(url)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"pg_dump failed ({proc.returncode}): {proc.stderr.strip()}")


def _pq_url(url: str) -> str:
    # pg_dump/libpq accept the SQLAlchemy URL as-is once the +driver part is
    # stripped (postgresql+psycopg2:// -> postgresql://).
    return re.sub(r"^postgresql\+[a-z0-9]+://", "postgresql://", url)


def backup_sqlite(url: str, dest: Path) -> None:
    """Online copy via SQLite's backup API — safe against concurrent writers."""
    source = create_engine(url, connect_args={"check_same_thread": False})
    try:
        raw = source.raw_connection()  # sqlite3.Connection
        try:
            raw.backup(dest_as_sqlite(dest))
        finally:
            raw.close()
    finally:
        source.dispose()


def dest_as_sqlite(dest: Path):
    """Open a plain sqlite3 connection to the destination file."""
    import sqlite3

    return sqlite3.connect(str(dest))


def make_backup(keep: int) -> Path:
    url = settings.DATABASE_URL
    if not _SAFE_URL_RE.match(url):
        raise RuntimeError(f"Unrecognized DATABASE_URL scheme: {url.split('://')[0]!r}")
    out_dir = _backup_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    if url.startswith("postgres"):
        dest = out_dir / f"smw-{_utc_stamp()}.dump"
        backup_postgres(url, dest)
    elif url.startswith("sqlite"):
        dest = out_dir / f"smw-{_utc_stamp()}.db"
        backup_sqlite(url, dest)
    else:
        raise RuntimeError(f"No backup strategy for {url.split('://')[0]!r}")

    size_kb = dest.stat().st_size / 1024
    print(f"Backup written: {dest} ({size_kb:.1f} KB)")
    prune_backups(keep)
    return dest


def list_backups() -> list[Path]:
    pattern = "smw-*.db" if settings.DATABASE_URL.startswith("sqlite") else "smw-*.dump"
    return sorted(_backup_dir().glob(pattern))


def prune_backups(keep: int) -> None:
    if keep <= 0:
        return
    stale = list_backups()[:-keep] if len(list_backups()) > keep else []
    for path in stale:
        path.unlink()
        print(f"Pruned old backup: {path.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smart Market Watchlist DB backup")
    parser.add_argument("--list", action="store_true", help="list existing backups and exit")
    parser.add_argument("--keep", type=int, default=7, help="backups to retain (default 7)")
    args = parser.parse_args()

    if args.list:
        for path in list_backups():
            print(path)
        return 0

    make_backup(args.keep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
