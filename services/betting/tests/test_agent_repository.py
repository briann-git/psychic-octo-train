"""Tests for AgentRepository."""

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from betting.models.agent import Agent, BanditPolicy
from betting.services.agent_repository import AgentRepository


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def repo(db_path):
    return AgentRepository(db_path=db_path)


class TestBootstrapAgents:
    def test_creates_all_four_agents(self, repo):
        repo.bootstrap_agents()
        agents = repo.get_all_agents()
        assert len(agents) == 4
        ids = {a.id for a in agents}
        assert ids == {"A", "B", "C", "D"}

    def test_correct_starting_policies(self, repo):
        repo.bootstrap_agents()
        a = repo.get_agent("A")
        assert a is not None
        assert a.policy.statistical_weight == pytest.approx(0.80)
        assert a.policy.market_weight == pytest.approx(0.20)
        assert a.policy.confidence_threshold == pytest.approx(0.62)
        assert a.policy.staking_strategy == "flat"
        assert a.bankroll == 1000.0

        d = repo.get_agent("D")
        assert d is not None
        assert d.policy.staking_strategy == "kelly"
        assert d.policy.kelly_fraction == pytest.approx(0.25)

    def test_idempotent_on_second_call(self, repo):
        repo.bootstrap_agents()
        # Modify agent A's bankroll
        a = repo.get_agent("A")
        a.bankroll = 900.0
        repo.save_agent(a)

        # Second bootstrap should not overwrite
        repo.bootstrap_agents()
        a2 = repo.get_agent("A")
        assert a2.bankroll == 900.0


class TestSaveAgent:
    def test_upserts_correctly(self, repo):
        agent = Agent(
            id="X",
            policy=BanditPolicy(
                statistical_weight=0.70,
                market_weight=0.30,
                confidence_threshold=0.65,
                staking_strategy="flat",
            ),
            bankroll=500.0,
            starting_bankroll=1000.0,
            created_at=datetime.now(tz=timezone.utc),
            last_updated_at=datetime.now(tz=timezone.utc),
        )
        repo.save_agent(agent)

        loaded = repo.get_agent("X")
        assert loaded is not None
        assert loaded.bankroll == 500.0

        # Update bankroll and re-save
        agent.bankroll = 600.0
        repo.save_agent(agent)
        reloaded = repo.get_agent("X")
        assert reloaded.bankroll == 600.0


class TestGetSettledSince:
    def test_returns_only_picks_settled_after_datetime(self, repo):
        repo.bootstrap_agents()
        now = datetime.now(tz=timezone.utc)

        # Record a pick for agent A
        repo.record_agent_pick("A", {
            "fixture_id": "fix-001",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "league": "PL",
            "kickoff": now.isoformat(),
            "season": "2025/26",
            "market": "double_chance",
            "selection": "1X",
            "odds": 1.50,
            "stake": 10.0,
            "confidence": 0.75,
            "expected_value": 0.10,
            "statistical_weight": 0.80,
            "market_weight": 0.20,
        })

        # Get the pick id
        unsettled = repo.get_unsettled_agent_picks("A")
        assert len(unsettled) == 1
        pick_id = unsettled[0]["id"]

        # Settle it
        repo.settle_agent_pick(pick_id, "won", 0.05, 5.0)

        # Query settled since yesterday — should return the pick
        yesterday = now - timedelta(days=1)
        settled = repo.get_settled_since("A", yesterday)
        assert len(settled) == 1
        assert settled[0]["outcome"] == "won"
        assert settled[0]["pnl"] == 5.0

        # Query settled since tomorrow — should return nothing
        tomorrow = now + timedelta(days=1)
        settled_future = repo.get_settled_since("A", tomorrow)
        assert len(settled_future) == 0

    def test_does_not_return_unsettled_picks(self, repo):
        repo.bootstrap_agents()
        now = datetime.now(tz=timezone.utc)

        repo.record_agent_pick("A", {
            "fixture_id": "fix-002",
            "home_team": "Liverpool",
            "away_team": "Spurs",
            "league": "PL",
            "kickoff": now.isoformat(),
            "season": "2025/26",
            "market": "double_chance",
            "selection": "1X",
            "odds": 1.40,
            "stake": 10.0,
            "confidence": 0.70,
            "expected_value": 0.08,
            "statistical_weight": 0.80,
            "market_weight": 0.20,
        })

        yesterday = now - timedelta(days=1)
        settled = repo.get_settled_since("A", yesterday)
        assert len(settled) == 0
