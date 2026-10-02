"""SQLite access (shared, frozen). WAL mode, foreign keys, sqlite-vec + FTS5.

Usage in routes:   def handler(db: sqlite3.Connection = Depends(get_db)): ...
Usage in scripts:  with connect() as db: ...
Run `python -m backend.app.db` (or `make migrate`) to create/upgrade the schema.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import sqlite_vec

from . import config

SCHEMA = Path(__file__).resolve().parents[1] / "db" / "schema.sql"
EMBED_DIM = 768

# Virtual tables need the extension loaded, so they live here rather than in schema.sql.
VIRTUAL_TABLES = f"""
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(text, tokenize='porter unicode61');
CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vectors USING vec0(
  matter_id INTEGER PARTITION KEY,
  embedding FLOAT[{EMBED_DIM}]
);
"""


def now_iso() -> str:
    """UTC timestamp like 2026-10-02T17:45:00Z (the Z form is safe in query strings, unlike +00:00)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _open(path: Path | str | None = None) -> sqlite3.Connection:
    p = Path(path or config.settings.db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


@contextmanager
def connect(path: Path | str | None = None) -> Iterator[sqlite3.Connection]:
    conn = _open(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: one connection per request, committed on success."""
    with connect() as conn:
        yield conn


def migrate(path: Path | str | None = None) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA.read_text())
        conn.executescript(VIRTUAL_TABLES)


def jload(value: str | None, default: Any = None) -> Any:
    if value is None or value == "":
        return default
    return json.loads(value)


def jdump(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


if __name__ == "__main__":
    migrate()
    print(f"schema applied → {config.settings.db_path}")
