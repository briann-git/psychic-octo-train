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
    recorded_at     TEXT NOT NULL,
    outcome         TEXT,
    settled_at      TEXT,
    selection_odds  REAL,
    season          TEXT,
    opening_odds    REAL
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
    recorded_at     TEXT NOT NULL,
    season          TEXT
);

DROP TABLE IF EXISTS odds_history;

CREATE TABLE IF NOT EXISTS odds_history (
    id              TEXT PRIMARY KEY,
    fixture_id      TEXT NOT NULL,
    league          TEXT NOT NULL,
    home_team       TEXT NOT NULL,
    away_team       TEXT NOT NULL,
    kickoff         TEXT NOT NULL,
    market          TEXT NOT NULL,
    bookmaker       TEXT NOT NULL,
    selections_json TEXT NOT NULL,
    snapshot_type   TEXT NOT NULL,
    fetched_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_odds_history_fixture
    ON odds_history (fixture_id, fetched_at);

CREATE TABLE IF NOT EXISTS fixture_calendar (
    id              TEXT PRIMARY KEY,
    home_team       TEXT NOT NULL,
    away_team       TEXT NOT NULL,
    league          TEXT NOT NULL,
    kickoff         TEXT NOT NULL,
    season          TEXT NOT NULL,
    fetched_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fixture_calendar_kickoff
    ON fixture_calendar (kickoff);

CREATE INDEX IF NOT EXISTS idx_fixture_calendar_league_kickoff
    ON fixture_calendar (league, kickoff);

CREATE TABLE IF NOT EXISTS pick_signals (
    id              TEXT PRIMARY KEY,
    pick_id         TEXT NOT NULL,
    agent_id        TEXT NOT NULL,
    recommendation  TEXT NOT NULL,
    confidence      REAL NOT NULL,
    edge            REAL NOT NULL,
    selection       TEXT NOT NULL,
    reasoning       TEXT,
    veto            INTEGER NOT NULL DEFAULT 0,
    veto_reason     TEXT,
    data_timestamp  TEXT NOT NULL,
    recorded_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pick_signals_pick_id
    ON pick_signals (pick_id);

CREATE INDEX IF NOT EXISTS idx_pick_signals_agent_id
    ON pick_signals (agent_id);

CREATE TABLE IF NOT EXISTS agent_states (
    id                      TEXT PRIMARY KEY,
    statistical_weight      REAL NOT NULL,
    market_weight           REAL NOT NULL,
    confidence_threshold    REAL NOT NULL,
    staking_strategy        TEXT NOT NULL,
    kelly_fraction          REAL NOT NULL DEFAULT 0.25,
    learning_rate           REAL NOT NULL DEFAULT 0.01,
    update_count            INTEGER NOT NULL DEFAULT 0,
    bankroll                REAL NOT NULL,
    starting_bankroll       REAL NOT NULL,
    total_picks             INTEGER NOT NULL DEFAULT 0,
    total_settled           INTEGER NOT NULL DEFAULT 0,
    created_at              TEXT NOT NULL,
    last_updated_at         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_picks (
    id                  TEXT PRIMARY KEY,
    agent_id            TEXT NOT NULL,
    fixture_id          TEXT NOT NULL,
    home_team           TEXT NOT NULL,
    away_team           TEXT NOT NULL,
    league              TEXT NOT NULL,
    kickoff             TEXT NOT NULL,
    season              TEXT NOT NULL,
    market              TEXT NOT NULL,
    selection           TEXT NOT NULL,
    odds                REAL NOT NULL,
    stake               REAL NOT NULL,
    confidence          REAL NOT NULL,
    expected_value      REAL NOT NULL,
    statistical_weight  REAL NOT NULL,
    market_weight       REAL NOT NULL,
    outcome             TEXT,
    clv                 REAL,
    pnl                 REAL,
    recorded_at         TEXT NOT NULL,
    settled_at          TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_picks_agent_id
    ON agent_picks (agent_id, recorded_at);

CREATE INDEX IF NOT EXISTS idx_agent_picks_fixture
    ON agent_picks (fixture_id);
"""

_MIGRATION_ADD_SETTLEMENT_COLUMNS = """
ALTER TABLE picks ADD COLUMN outcome TEXT;
ALTER TABLE picks ADD COLUMN settled_at TEXT;
"""

class SqliteLedgerRepository(ILedgerRepository):
    def __init__(self, db_path: str, flat_stake: float = 10.0) -> None:
        self._db_path = db_path
        self._flat_stake = flat_stake
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_DDL)
            self._migrate(conn)

    def _migrate(self, conn: sqlite3.Connection) -> None:
        """Applies schema migrations guarded by column existence checks."""
        cols = {row[1] for row in conn.execute("PRAGMA table_info(picks)")}
        if "outcome" not in cols:
            conn.execute("ALTER TABLE picks ADD COLUMN outcome TEXT")
        if "settled_at" not in cols:
            conn.execute("ALTER TABLE picks ADD COLUMN settled_at TEXT")
        if "selection_odds" not in cols:
            conn.execute("ALTER TABLE picks ADD COLUMN selection_odds REAL")
        if "season" not in cols:
            conn.execute("ALTER TABLE picks ADD COLUMN season TEXT")

        if "opening_odds" not in cols:
            conn.execute("ALTER TABLE picks ADD COLUMN opening_odds REAL")

        skip_cols = {row[1] for row in conn.execute("PRAGMA table_info(skips)")}
        if "season" not in skip_cols:
            conn.execute("ALTER TABLE skips ADD COLUMN season TEXT")

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
        selection_odds = odds.selections.get(selection, 0.0)

        # Fetch opening odds from earliest odds_history snapshot
        opening_odds = self._get_opening_odds(fixture.id, selection)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO picks
                (id, fixture_id, home_team, away_team, league, kickoff,
                 market, selection, odds, stake, confidence, expected_value,
                 recorded_at, selection_odds, season, opening_odds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    selection_odds,
                    self._flat_stake,
                    verdict.consensus_confidence,
                    verdict.expected_value,
                    datetime.now(tz=timezone.utc).isoformat(),
                    selection_odds,
                    fixture.season,
                    opening_odds,
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
                 market, skip_reason, confidence, errors, recorded_at, season)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    fixture.season,
                ),
            )

    def save_odds_snapshot(
        self,
        fixture: Fixture,
        odds: OddsSnapshot,
        snapshot_type: str,
    ) -> None:
        """
        Persists an odds snapshot to odds_history.
        Skips if a row already exists for fixture_id + snapshot_type.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT id FROM odds_history WHERE fixture_id = ? AND snapshot_type = ?",
                (fixture.id, snapshot_type),
            )
            if cursor.fetchone() is not None:
                return

            selections_json = json.dumps(odds.selections)

            conn.execute(
                """
                INSERT INTO odds_history
                (id, fixture_id, league, home_team, away_team, kickoff,
                 market, bookmaker, selections_json,
                 snapshot_type, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    fixture.id,
                    fixture.league,
                    fixture.home_team,
                    fixture.away_team,
                    fixture.kickoff.isoformat(),
                    odds.market,
                    odds.bookmaker,
                    selections_json,
                    snapshot_type,
                    datetime.now(tz=timezone.utc).isoformat(),
                ),
            )

    def get_odds_history(self, fixture_id: str) -> list[dict]:
        """Returns all rows for fixture ordered by fetched_at ascending."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM odds_history WHERE fixture_id = ? ORDER BY fetched_at ASC",
                (fixture_id,),
            )
            cols = [desc[0] for desc in cursor.description]
            rows = []
            for row in cursor.fetchall():
                d = dict(zip(cols, row))
                if "selections_json" in d:
                    d["selections"] = json.loads(d["selections_json"])
                rows.append(d)
            return rows

    def get_pending_picks(self) -> list[dict]:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM picks WHERE outcome IS NULL"
            )
            cols = [desc[0] for desc in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def settle_pick(self, pick_id: str, outcome: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE picks SET outcome = ?, settled_at = ?
                WHERE id = ?
                """,
                (outcome, datetime.now(tz=timezone.utc).isoformat(), pick_id),
            )

    def get_all_picks(self) -> list[dict]:
        with self._connect() as conn:
            cursor = conn.execute("SELECT * FROM picks")
            cols = [desc[0] for desc in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def get_all_skips(self) -> list[dict]:
        with self._connect() as conn:
            cursor = conn.execute("SELECT * FROM skips")
            cols = [desc[0] for desc in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def record_pick_signals(
        self,
        pick_id: str,
        signals: list[dict],
    ) -> None:
        now = datetime.now(tz=timezone.utc).isoformat()
        with self._connect() as conn:
            for signal in signals:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO pick_signals
                    (id, pick_id, agent_id, recommendation, confidence, edge,
                     selection, reasoning, veto, veto_reason, data_timestamp, recorded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        pick_id,
                        signal.get("agent_id", ""),
                        signal.get("recommendation", ""),
                        signal.get("confidence", 0.0),
                        signal.get("edge", 0.0),
                        signal.get("selection", ""),
                        signal.get("reasoning"),
                        int(signal.get("veto", False)),
                        signal.get("veto_reason"),
                        signal.get("data_timestamp", ""),
                        now,
                    ),
                )

    def _get_opening_odds(self, fixture_id: str, selection: str) -> float | None:
        """
        Returns the decimal odds for the given selection from the earliest
        odds_history snapshot. Returns None if no history exists yet.
        """
        history = self.get_odds_history(fixture_id)
        if not history:
            return None
        earliest = history[0]   # already ordered ASC by fetched_at
        selections = earliest.get("selections", {})
        return selections.get(selection)

    def upsert_fixture_calendar(self, fixtures: list[Fixture]) -> None:
        now = datetime.now(tz=timezone.utc).isoformat()
        with self._connect() as conn:
            # Prune past fixtures
            conn.execute(
                "DELETE FROM fixture_calendar WHERE kickoff < ?",
                (datetime.now(tz=timezone.utc).isoformat(),),
            )
            # Upsert upcoming fixtures
            for fixture in fixtures:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO fixture_calendar
                    (id, home_team, away_team, league, kickoff, season, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        fixture.id,
                        fixture.home_team,
                        fixture.away_team,
                        fixture.league,
                        fixture.kickoff.isoformat(),
                        fixture.season,
                        now,
                    ),
                )

    def get_calendar_fixtures(
        self,
        from_dt: datetime,
        to_dt: datetime,
        leagues: list[str] | None = None,
    ) -> list[dict]:
        query = """
            SELECT * FROM fixture_calendar
            WHERE kickoff >= ? AND kickoff <= ?
        """
        params: list = [from_dt.isoformat(), to_dt.isoformat()]

        if leagues:
            placeholders = ",".join("?" * len(leagues))
            query += f" AND league IN ({placeholders})"
            params.extend(leagues)

        query += " ORDER BY kickoff ASC"

        with self._connect() as conn:
            cursor = conn.execute(query, params)
            cols = [desc[0] for desc in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
