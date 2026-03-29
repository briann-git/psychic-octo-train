import json
import sqlite3
import uuid
from datetime import datetime, timezone

from betting.graph.state import BettingState
from betting.interfaces.ledger_repository import ILedgerRepository
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot
from betting.models.verdict import Verdict

_DDL = """
CREATE TABLE IF NOT EXISTS picks (
    id              TEXT PRIMARY KEY,
    fixture_id      TEXT NOT NULL,
    home_team       TEXT NOT NULL,
    away_team       TEXT NOT NULL,
    league          TEXT NOT NULL,
    kickoff         TEXT NOT NULL,
    market          TEXT NOT NULL,
    selection       TEXT NOT NULL,
    odds            REAL NOT NULL,
    stake           REAL NOT NULL,
    confidence      REAL NOT NULL,
    expected_value  REAL NOT NULL,
    recorded_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skips (
    id              TEXT PRIMARY KEY,
    fixture_id      TEXT NOT NULL,
    home_team       TEXT NOT NULL,
    away_team       TEXT NOT NULL,
    league          TEXT NOT NULL,
    kickoff         TEXT NOT NULL,
    market          TEXT NOT NULL,
    skip_reason     TEXT NOT NULL,
    confidence      REAL,
    errors          TEXT,
    recorded_at     TEXT NOT NULL
);
"""

_ODDS_COLUMN = {
    "1X": "home_draw",
    "12": "home_away",
    "X2": "draw_away",
}


class SqliteLedgerRepository(ILedgerRepository):
    def __init__(self, db_path: str, flat_stake: float = 10.0) -> None:
        self._db_path = db_path
        self._flat_stake = flat_stake
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_DDL)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def record(self, state: BettingState) -> None:
        verdict = Verdict.from_dict(state["verdict"])  # type: ignore[arg-type]
        fixture = Fixture.from_dict(state["fixture"])
        odds = OddsSnapshot.from_dict(state["odds_snapshot"])

        if verdict.recommendation == "back":
            self._write_pick(fixture, odds, verdict)
        else:
            self._write_skip(fixture, odds, verdict, state.get("errors", []))

    def get_by_fixture(self, fixture_id: str) -> dict | None:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM picks WHERE fixture_id = ?", (fixture_id,)
            )
            row = cursor.fetchone()
            if row:
                cols = [desc[0] for desc in cursor.description]
                return dict(zip(cols, row))

            cursor = conn.execute(
                "SELECT * FROM skips WHERE fixture_id = ?", (fixture_id,)
            )
            row = cursor.fetchone()
            if row:
                cols = [desc[0] for desc in cursor.description]
                return dict(zip(cols, row))

        return None

    def _write_pick(
        self,
        fixture: Fixture,
        odds: OddsSnapshot,
        verdict: Verdict,
    ) -> None:
        selection = verdict.selection
        odds_col = _ODDS_COLUMN.get(selection, "home_draw")
        odds_value = getattr(odds, odds_col, odds.home_draw)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO picks
                (id, fixture_id, home_team, away_team, league, kickoff,
                 market, selection, odds, stake, confidence, expected_value, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    fixture.id,
                    fixture.home_team,
                    fixture.away_team,
                    fixture.league,
                    fixture.kickoff.isoformat(),
                    verdict.market,
                    selection,
                    odds_value,
                    self._flat_stake,
                    verdict.consensus_confidence,
                    verdict.expected_value,
                    datetime.now(tz=timezone.utc).isoformat(),
                ),
            )

    def _write_skip(
        self,
        fixture: Fixture,
        odds: OddsSnapshot,
        verdict: Verdict,
        errors: list[str],
    ) -> None:
        skip_reason = verdict.skip_reason or verdict.recommendation
        errors_json = json.dumps(errors) if errors else None

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO skips
                (id, fixture_id, home_team, away_team, league, kickoff,
                 market, skip_reason, confidence, errors, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    fixture.id,
                    fixture.home_team,
                    fixture.away_team,
                    fixture.league,
                    fixture.kickoff.isoformat(),
                    verdict.market,
                    skip_reason,
                    verdict.consensus_confidence,
                    errors_json,
                    datetime.now(tz=timezone.utc).isoformat(),
                ),
            )
