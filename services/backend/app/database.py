import sqlite3
from contextlib import contextmanager

from app.config import DB_PATH


@contextmanager
def get_db():
    """Read-only DB connection."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_rw_db():
    """Read-write DB connection."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


def resolve_profile_id(conn, profile: str | None) -> str | None:
    """Return profile_id from param, or fall back to the active profile."""
    if profile:
        return profile
    row = conn.execute("SELECT id FROM profiles WHERE is_active = 1 LIMIT 1").fetchone()
    return row["id"] if row else None
