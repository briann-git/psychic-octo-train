"""Persistence layer for agent state and per-agent picks."""

import sqlite3
import uuid
from datetime import datetime, timezone

from betting.models.agent import Agent, BanditPolicy

_AGENT_DDL = """
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


class AgentRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_AGENT_DDL)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def get_all_agents(self) -> list[Agent]:
        """Returns all agents from agent_states."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT * FROM agent_states ORDER BY id")
            cols = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
        return [self._row_to_agent(dict(zip(cols, row))) for row in rows]

    def get_agent(self, agent_id: str) -> Agent | None:
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM agent_states WHERE id = ?", (agent_id,)
            )
            cols = [desc[0] for desc in cursor.description]
            row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_agent(dict(zip(cols, row)))

    def save_agent(self, agent: Agent) -> None:
        """Upserts agent state."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO agent_states
                (id, statistical_weight, market_weight, confidence_threshold,
                 staking_strategy, kelly_fraction, learning_rate, update_count,
                 bankroll, starting_bankroll, total_picks, total_settled,
                 created_at, last_updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ),
            )

    def record_agent_pick(self, agent_id: str, pick: dict) -> None:
        """Writes a row to agent_picks."""
        now = datetime.now(tz=timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_picks
                (id, agent_id, fixture_id, home_team, away_team, league,
                 kickoff, season, market, selection, odds, stake,
                 confidence, expected_value, statistical_weight,
                 market_weight, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    now,
                ),
            )

    def get_unsettled_agent_picks(self, agent_id: str) -> list[dict]:
        """Returns agent_picks where outcome IS NULL."""
        with self._connect() as conn:
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
    ) -> list[dict]:
        """Returns settled picks since a given datetime — used by recalibration."""
        with self._connect() as conn:
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

    def bootstrap_agents(self) -> None:
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
                bankroll=1000.0,
                starting_bankroll=1000.0,
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
                bankroll=1000.0,
                starting_bankroll=1000.0,
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
                bankroll=1000.0,
                starting_bankroll=1000.0,
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
                bankroll=1000.0,
                starting_bankroll=1000.0,
                created_at=now,
                last_updated_at=now,
            ),
        ]
        for agent in default_agents:
            existing = self.get_agent(agent.id)
            if not existing:
                self.save_agent(agent)

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
