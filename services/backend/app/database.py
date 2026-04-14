import sqlite3
from contextlib import contextmanager

from app.config import BACKTEST_DB_PATH, DB_PATH


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


def resolve_profile_db(profile_id: str | None) -> tuple[str | None, str]:
    """Look up profile type from ledger.db and return (resolved_id, db_path)."""
    try:
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5) as c:
            c.row_factory = sqlite3.Row
            if profile_id:
                row = c.execute(
                    "SELECT id, type FROM profiles WHERE id = ?", (profile_id,)
                ).fetchone()
            else:
                row = c.execute(
                    "SELECT id, type FROM profiles WHERE is_active = 1 LIMIT 1"
                ).fetchone()
            if row:
                return row["id"], (BACKTEST_DB_PATH if row["type"] == "backtest" else DB_PATH)
    except Exception:
        pass
    return profile_id, DB_PATH


@contextmanager
def get_db_for_profile(profile: str | None = None):
    """Read-only connection routed to ledger.db or backtest.db. Yields (conn, resolved_pid)."""
    pid, db_path = resolve_profile_db(profile)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        yield conn, pid
    finally:
        conn.close()


@contextmanager
def get_rw_db_for_profile(profile: str | None = None):
    """Read-write connection routed to ledger.db or backtest.db. Yields (conn, resolved_pid)."""
    pid, db_path = resolve_profile_db(profile)
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn, pid
    finally:
        conn.close()
