"""Persistence layer for agent state and per-agent picks."""

import sqlite3
import uuid
from datetime import datetime, timezone

from betting.models.agent import Agent, BanditPolicy

_AGENT_DDL = """
CREATE TABLE IF NOT EXISTS agent_states (
    id                      TEXT NOT NULL,
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
    last_updated_at         TEXT NOT NULL,
    profile_id              TEXT,
    PRIMARY KEY (id, profile_id)
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
    stat_confidence     REAL,
    stat_edge           REAL,
    market_confidence   REAL,
    market_edge         REAL,
    outcome             TEXT,
    clv                 REAL,
    pnl                 REAL,
    recorded_at         TEXT NOT NULL,
    settled_at          TEXT,
    profile_id          TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_picks_agent_id
    ON agent_picks (agent_id, recorded_at);

CREATE INDEX IF NOT EXISTS idx_agent_picks_fixture
    ON agent_picks (fixture_id);
"""


class AgentRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_AGENT_DDL)
            self._migrate(conn)

    def _migrate(self, conn: sqlite3.Connection) -> None:
        """Applies schema migrations guarded by column existence checks."""
        cols = {row[1] for row in conn.execute("PRAGMA table_info(agent_picks)")}
        for col in ("stat_confidence", "stat_edge", "market_confidence", "market_edge"):
            if col not in cols:
                conn.execute(f"ALTER TABLE agent_picks ADD COLUMN {col} REAL")
        if "profile_id" not in cols:
            conn.execute("ALTER TABLE agent_picks ADD COLUMN profile_id TEXT")
            conn.execute(
                "UPDATE agent_picks SET profile_id = 'default-paper' WHERE profile_id IS NULL"
            )

        state_cols = {row[1] for row in conn.execute("PRAGMA table_info(agent_states)")}
        if "profile_id" not in state_cols:
            # Column doesn't exist yet — add it and backfill, then rebuild
            # the table so the composite PK (id, profile_id) is enforced.
            conn.execute("ALTER TABLE agent_states ADD COLUMN profile_id TEXT")
            conn.execute(
                "UPDATE agent_states SET profile_id = 'default-paper' WHERE profile_id IS NULL"
            )
            self._rebuild_agent_states(conn)
        elif not self._has_composite_pk(conn):
            # Column exists (from a previous partial migration) but PK is
            # still single-column — rebuild to get the composite PK.
            conn.execute(
                "UPDATE agent_states SET profile_id = 'default-paper' WHERE profile_id IS NULL"
            )
            self._rebuild_agent_states(conn)

        # Create profile indexes after columns are guaranteed to exist
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_states_profile ON agent_states (profile_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_picks_profile ON agent_picks (profile_id)")

    @staticmethod
    def _has_composite_pk(conn: sqlite3.Connection) -> bool:
        """Return True if agent_states PK already spans (id, profile_id)."""
        pk_cols = [
            row[1]
            for row in conn.execute("PRAGMA table_info(agent_states)")
            if row[5]  # pk flag > 0
        ]
        return "id" in pk_cols and "profile_id" in pk_cols

    @staticmethod
    def _rebuild_agent_states(conn: sqlite3.Connection) -> None:
        """SQLite 12-step rebuild to enforce composite PK (id, profile_id)."""
        conn.executescript("""
            CREATE TABLE agent_states_new (
                id                      TEXT NOT NULL,
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
                last_updated_at         TEXT NOT NULL,
                profile_id              TEXT,
                PRIMARY KEY (id, profile_id)
            );

            INSERT INTO agent_states_new
                SELECT id, statistical_weight, market_weight, confidence_threshold,
                       staking_strategy, kelly_fraction, learning_rate, update_count,
                       bankroll, starting_bankroll, total_picks, total_settled,
                       created_at, last_updated_at, profile_id
                FROM agent_states;

            DROP TABLE agent_states;

            ALTER TABLE agent_states_new RENAME TO agent_states;
        """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def get_all_agents(self, profile_id: str | None = None) -> list[Agent]:
        """Returns all agents, optionally filtered by profile."""
        with self._connect() as conn:
            if profile_id is not None:
                cursor = conn.execute(
                    "SELECT * FROM agent_states WHERE profile_id = ? ORDER BY id",
                    (profile_id,),
                )
            else:
                cursor = conn.execute("SELECT * FROM agent_states ORDER BY id")
            cols = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
        return [self._row_to_agent(dict(zip(cols, row))) for row in rows]

    def get_agent(self, agent_id: str, profile_id: str | None = None) -> Agent | None:
        with self._connect() as conn:
            if profile_id is not None:
                cursor = conn.execute(
                    "SELECT * FROM agent_states WHERE id = ? AND profile_id = ?",
                    (agent_id, profile_id),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM agent_states WHERE id = ?", (agent_id,)
                )
            cols = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_agent(dict(zip(cols, row)))

    def save_agent(self, agent: Agent, profile_id: str = "default-paper") -> None:
        """Upserts agent state."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO agent_states
                (id, statistical_weight, market_weight, confidence_threshold,
                 staking_strategy, kelly_fraction, learning_rate, update_count,
                 bankroll, starting_bankroll, total_picks, total_settled,
                 created_at, last_updated_at, profile_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    agent.id,
                    agent.policy.statistical_weight,
                    agent.policy.market_weight,
                    agent.policy.confidence_threshold,
                    agent.policy.staking_strategy,
                    agent.policy.kelly_fraction,
                    agent.policy.learning_rate,
                    agent.policy.update_count,
                    agent.bankroll,
                    agent.starting_bankroll,
                    agent.total_picks,
                    agent.total_settled,
                    agent.created_at.isoformat(),
                    agent.last_updated_at.isoformat(),
                    profile_id,
                ),
            )

    def record_agent_pick(self, agent_id: str, pick: dict, profile_id: str = "default-paper") -> None:
        """Writes a row to agent_picks."""
        now = datetime.now(tz=timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_picks
                (id, agent_id, fixture_id, home_team, away_team, league,
                 kickoff, season, market, selection, odds, stake,
                 confidence, expected_value, statistical_weight,
                 market_weight, stat_confidence, stat_edge,
                 market_confidence, market_edge, recorded_at, profile_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    agent_id,
                    pick["fixture_id"],
                    pick["home_team"],
                    pick["away_team"],
                    pick["league"],
                    pick["kickoff"],
                    pick["season"],
                    pick["market"],
                    pick["selection"],
                    pick["odds"],
                    pick["stake"],
                    pick["confidence"],
                    pick["expected_value"],
                    pick["statistical_weight"],
                    pick["market_weight"],
                    pick.get("stat_confidence"),
                    pick.get("stat_edge"),
                    pick.get("market_confidence"),
                    pick.get("market_edge"),
                    now,
                    profile_id,
                ),
            )

    def get_unsettled_agent_picks(self, agent_id: str, profile_id: str | None = None) -> list[dict]:
        """Returns agent_picks where outcome IS NULL."""
        with self._connect() as conn:
            if profile_id is not None:
                cursor = conn.execute(
                    "SELECT * FROM agent_picks WHERE agent_id = ? AND profile_id = ? AND outcome IS NULL",
                    (agent_id, profile_id),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM agent_picks WHERE agent_id = ? AND outcome IS NULL",
                    (agent_id,),
                )
            cols = [desc[0] for desc in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def settle_agent_pick(
        self,
        pick_id: str,
        outcome: str,
        clv: float | None,
        pnl: float,
    ) -> None:
        now = datetime.now(tz=timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE agent_picks
                SET outcome = ?, clv = ?, pnl = ?, settled_at = ?
                WHERE id = ?
                """,
                (outcome, clv, pnl, now, pick_id),
            )

    def get_settled_since(
        self,
        agent_id: str,
        since: datetime,
        profile_id: str | None = None,
    ) -> list[dict]:
        """Returns settled picks since a given datetime — used by recalibration."""
        with self._connect() as conn:
            if profile_id is not None:
                cursor = conn.execute(
                    """
                    SELECT * FROM agent_picks
                    WHERE agent_id = ? AND outcome IS NOT NULL AND settled_at >= ?
                          AND profile_id = ?
                    ORDER BY settled_at ASC
                    """,
                    (agent_id, since.isoformat(), profile_id),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM agent_picks
                    WHERE agent_id = ? AND outcome IS NOT NULL AND settled_at >= ?
                    ORDER BY settled_at ASC
                    """,
                    (agent_id, since.isoformat()),
                )
            cols = [desc[0] for desc in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def bootstrap_agents(self, profile_id: str = "default-paper", bankroll_start: float = 1000.0) -> None:
        """
        Creates the four agents with starting policies if they don't exist.
        Called once on first run. Idempotent — skips agents that already exist.
        """
        now = datetime.now(tz=timezone.utc)
        default_agents = [
            Agent(
                id="A",
                policy=BanditPolicy(
                    statistical_weight=0.80,
                    market_weight=0.20,
                    confidence_threshold=0.62,
                    staking_strategy="flat",
                ),
                bankroll=bankroll_start,
                starting_bankroll=bankroll_start,
                created_at=now,
                last_updated_at=now,
            ),
            Agent(
                id="B",
                policy=BanditPolicy(
                    statistical_weight=0.40,
                    market_weight=0.60,
                    confidence_threshold=0.65,
                    staking_strategy="flat",
                ),
                bankroll=bankroll_start,
                starting_bankroll=bankroll_start,
                created_at=now,
                last_updated_at=now,
            ),
            Agent(
                id="C",
                policy=BanditPolicy(
                    statistical_weight=0.60,
                    market_weight=0.40,
                    confidence_threshold=0.70,
                    staking_strategy="flat",
                ),
                bankroll=bankroll_start,
                starting_bankroll=bankroll_start,
                created_at=now,
                last_updated_at=now,
            ),
            Agent(
                id="D",
                policy=BanditPolicy(
                    statistical_weight=0.50,
                    market_weight=0.50,
                    confidence_threshold=0.60,
                    staking_strategy="kelly",
                    kelly_fraction=0.25,
                ),
                bankroll=bankroll_start,
                starting_bankroll=bankroll_start,
                created_at=now,
                last_updated_at=now,
            ),
        ]
        for agent in default_agents:
            existing = self.get_agent(agent.id, profile_id)
            if not existing:
                self.save_agent(agent, profile_id)

    @staticmethod
    def _row_to_agent(row: dict) -> Agent:
        created = datetime.fromisoformat(row["created_at"])
        updated = datetime.fromisoformat(row["last_updated_at"])
        return Agent(
            id=row["id"],
            policy=BanditPolicy(
                statistical_weight=row["statistical_weight"],
                market_weight=row["market_weight"],
                confidence_threshold=row["confidence_threshold"],
                staking_strategy=row["staking_strategy"],
                kelly_fraction=row["kelly_fraction"],
                learning_rate=row["learning_rate"],
                update_count=row["update_count"],
            ),
            bankroll=row["bankroll"],
            starting_bankroll=row["starting_bankroll"],
            total_picks=row["total_picks"],
            total_settled=row["total_settled"],
            created_at=created,
            last_updated_at=updated,
        )
