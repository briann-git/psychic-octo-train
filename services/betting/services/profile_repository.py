"""Persistence layer for trading profiles."""

import sqlite3
from datetime import datetime, timezone

from betting.models.profile import Profile

DEFAULT_PROFILE_ID = "default-paper"


class ProfileRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id              TEXT PRIMARY KEY,
                    name            TEXT NOT NULL,
                    type            TEXT NOT NULL DEFAULT 'paper',
                    bankroll_start  REAL NOT NULL DEFAULT 1000.0,
                    is_active       INTEGER NOT NULL DEFAULT 0,
                    created_at      TEXT NOT NULL
                )
            """)
            # Ensure default paper profile exists
            row = conn.execute(
                "SELECT id FROM profiles WHERE id = ?", (DEFAULT_PROFILE_ID,)
            ).fetchone()
            if row is None:
                conn.execute(
                    """
                    INSERT INTO profiles (id, name, type, bankroll_start, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        DEFAULT_PROFILE_ID,
                        "Paper \u2013 Default",
                        "paper",
                        1000.0,
                        1,
                        datetime.now(tz=timezone.utc).isoformat(),
                    ),
                )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def create(self, profile: Profile) -> Profile:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO profiles (id, name, type, bankroll_start, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.id,
                    profile.name,
                    profile.type,
                    profile.bankroll_start,
                    int(profile.is_active),
                    profile.created_at.isoformat(),
                ),
            )
        return profile

    def get(self, profile_id: str) -> Profile | None:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM profiles WHERE id = ?", (profile_id,)
            )
            cols = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_profile(dict(zip(cols, row)))

    def get_active(self) -> Profile | None:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM profiles WHERE is_active = 1 LIMIT 1"
            )
            cols = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_profile(dict(zip(cols, row)))

    def list_all(self) -> list[Profile]:
        with self._connect() as conn:
            cursor = conn.execute("SELECT * FROM profiles ORDER BY created_at ASC")
            cols = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
        return [self._row_to_profile(dict(zip(cols, row))) for row in rows]

    def set_active(self, profile_id: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE profiles SET is_active = 0")
            conn.execute(
                "UPDATE profiles SET is_active = 1 WHERE id = ?", (profile_id,)
            )

    def update(self, profile: Profile) -> Profile:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE profiles
                SET name = ?, type = ?, bankroll_start = ?, is_active = ?
                WHERE id = ?
                """,
                (
                    profile.name,
                    profile.type,
                    profile.bankroll_start,
                    int(profile.is_active),
                    profile.id,
                ),
            )
        return profile

    def delete(self, profile_id: str) -> None:
        with self._connect() as conn:
            # Guard: cannot delete the active profile
            row = conn.execute(
                "SELECT is_active FROM profiles WHERE id = ?", (profile_id,)
            ).fetchone()
            if row is None:
                raise ValueError(f"Profile {profile_id!r} not found")
            if row[0]:
                raise ValueError("Cannot delete the active profile")
            conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))

    @staticmethod
    def _row_to_profile(row: dict) -> Profile:
        return Profile(
            id=row["id"],
            name=row["name"],
            type=row["type"],
            bankroll_start=row["bankroll_start"],
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
