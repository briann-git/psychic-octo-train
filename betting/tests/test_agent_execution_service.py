"""Tests for AgentExecutionService."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from betting.models.agent import Agent, BanditPolicy
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot
from betting.models.verdict import Verdict
from betting.services.agent_execution_service import AgentExecutionService
from betting.services.agent_repository import AgentRepository


def _make_agent(
    agent_id: str = "A",
    stat_weight: float = 0.80,
    market_weight: float = 0.20,
    threshold: float = 0.62,
    staking: str = "flat",
    kelly_fraction: float = 0.25,
    bankroll: float = 1000.0,
) -> Agent:
    return Agent(
        id=agent_id,
        policy=BanditPolicy(
            statistical_weight=stat_weight,
            market_weight=market_weight,
            confidence_threshold=threshold,
            staking_strategy=staking,
            kelly_fraction=kelly_fraction,
        ),
        bankroll=bankroll,
        starting_bankroll=1000.0,
        created_at=datetime.now(tz=timezone.utc),
        last_updated_at=datetime.now(tz=timezone.utc),
    )


def _make_fixture() -> Fixture:
    return Fixture(
        id="fix-001",
        home_team="Arsenal",
        away_team="Chelsea",
        league="PL",
        season="2025/26",
        matchday=1,
        kickoff=datetime(2026, 4, 1, 15, 0, tzinfo=timezone.utc),
    )


def _make_odds() -> OddsSnapshot:
    return OddsSnapshot(
        fixture_id="fix-001",
        market="double_chance",
        bookmaker="pinnacle",
        selections={"1X": 1.50, "12": 1.30, "X2": 2.10},
        fetched_at=datetime.now(tz=timezone.utc),
    )


def _make_verdict() -> Verdict:
    return Verdict(
        fixture_id="fix-001",
        market="double_chance",
        recommendation="back",
        consensus_confidence=0.75,
        expected_value=0.10,
        signals_used=2,
        synthesised_at=datetime.now(tz=timezone.utc),
        selection="1X",
    )


def _make_signals(
    stat_confidence: float = 0.80,
    market_confidence: float = 0.70,
    stat_edge: float = 0.10,
    market_edge: float = 0.05,
) -> list[dict]:
    return [
        {
            "agent_id": "statistical",
            "confidence": stat_confidence,
            "edge": stat_edge,
        },
        {
            "agent_id": "market",
            "confidence": market_confidence,
            "edge": market_edge,
        },
    ]


def _make_service(agents: list[Agent] | None = None) -> tuple[AgentExecutionService, MagicMock]:
    repo = MagicMock(spec=AgentRepository)
    repo.get_all_agents.return_value = agents or [_make_agent()]
    service = AgentExecutionService(agent_repo=repo, flat_stake=10.0)
    return service, repo


class TestAgentSkipsWhenConfidenceBelowThreshold:
    def test_skips_when_weighted_confidence_below_threshold(self):
        # Agent threshold is 0.62 — signals with low confidence should be skipped
        agent = _make_agent(threshold=0.90)  # very high threshold
        service, repo = _make_service([agent])
        service.execute(_make_verdict(), _make_fixture(), _make_odds(), _make_signals())
        repo.record_agent_pick.assert_not_called()


class TestAgentSkipsWhenEdgeLessThanZero:
    def test_skips_when_weighted_edge_zero(self):
        agent = _make_agent(threshold=0.50)
        service, repo = _make_service([agent])
        signals = _make_signals(stat_edge=0.0, market_edge=0.0)
        service.execute(_make_verdict(), _make_fixture(), _make_odds(), signals)
        repo.record_agent_pick.assert_not_called()

    def test_skips_when_weighted_edge_negative(self):
        agent = _make_agent(threshold=0.50)
        service, repo = _make_service([agent])
        signals = _make_signals(stat_edge=-0.05, market_edge=-0.10)
        service.execute(_make_verdict(), _make_fixture(), _make_odds(), signals)
        repo.record_agent_pick.assert_not_called()


class TestAgentSkipsWhenBankrollInsufficient:
    def test_skips_when_bankroll_zero(self):
        agent = _make_agent(bankroll=0.0, threshold=0.50)
        service, repo = _make_service([agent])
        service.execute(_make_verdict(), _make_fixture(), _make_odds(), _make_signals())
        repo.record_agent_pick.assert_not_called()

    def test_skips_when_bankroll_less_than_stake(self):
        agent = _make_agent(bankroll=5.0, threshold=0.50)
        service, repo = _make_service([agent])
        service.execute(_make_verdict(), _make_fixture(), _make_odds(), _make_signals())
        repo.record_agent_pick.assert_not_called()


class TestFlatStakeAgent:
    def test_flat_stake_uses_configured_value(self):
        agent = _make_agent(threshold=0.50)
        service, repo = _make_service([agent])
        service.execute(_make_verdict(), _make_fixture(), _make_odds(), _make_signals())
        repo.record_agent_pick.assert_called_once()
        pick = repo.record_agent_pick.call_args[0][1]
        assert pick["stake"] == 10.0


class TestKellyStakeAgent:
    def test_kelly_stake_scales_with_edge_and_bankroll(self):
        agent = _make_agent(
            staking="kelly",
            kelly_fraction=0.25,
            threshold=0.50,
            bankroll=1000.0,
        )
        service, repo = _make_service([agent])
        signals = _make_signals(stat_edge=0.10, market_edge=0.10)
        service.execute(_make_verdict(), _make_fixture(), _make_odds(), signals)
        repo.record_agent_pick.assert_called_once()
        pick = repo.record_agent_pick.call_args[0][1]
        # Kelly: edge * kelly_fraction * bankroll = 0.10 * 0.25 * 1000 = 25.0
        assert pick["stake"] == 25.0

    def test_kelly_stake_capped_at_10_percent_bankroll(self):
        agent = _make_agent(
            staking="kelly",
            kelly_fraction=0.50,
            threshold=0.50,
            bankroll=100.0,
        )
        service, repo = _make_service([agent])
        # Very high edge to trigger cap
        signals = _make_signals(stat_edge=0.80, market_edge=0.80)
        service.execute(_make_verdict(), _make_fixture(), _make_odds(), signals)
        repo.record_agent_pick.assert_called_once()
        pick = repo.record_agent_pick.call_args[0][1]
        # Cap: 10% of 100 = 10.0
        assert pick["stake"] == 10.0


class TestBankrollDecrement:
    def test_bankroll_decremented_on_back_decision(self):
        agent = _make_agent(bankroll=1000.0, threshold=0.50)
        service, repo = _make_service([agent])
        service.execute(_make_verdict(), _make_fixture(), _make_odds(), _make_signals())
        # Agent bankroll should have been decremented by flat_stake (10.0)
        saved_agent = repo.save_agent.call_args[0][0]
        assert saved_agent.bankroll == 990.0
        assert saved_agent.total_picks == 1


class TestPickRecordedWithPolicySnapshot:
    def test_pick_includes_policy_snapshot(self):
        agent = _make_agent(
            stat_weight=0.80,
            market_weight=0.20,
            threshold=0.50,
        )
        service, repo = _make_service([agent])
        service.execute(_make_verdict(), _make_fixture(), _make_odds(), _make_signals())
        repo.record_agent_pick.assert_called_once()
        pick = repo.record_agent_pick.call_args[0][1]
        assert pick["statistical_weight"] == 0.80
        assert pick["market_weight"] == 0.20
        assert pick["fixture_id"] == "fix-001"
        assert pick["selection"] == "1X"
        assert pick["market"] == "double_chance"
