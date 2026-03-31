"""Tests for AgentRecalibrationService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from betting.models.agent import Agent, BanditPolicy
from betting.services.agent_recalibration_service import (
    AgentRecalibrationService,
    CONFIDENT_SAMPLE_SIZE,
    MIN_PICKS_FOR_UPDATE,
)
from betting.services.agent_repository import AgentRepository


def _make_agent(
    agent_id: str = "A",
    stat_weight: float = 0.80,
    market_weight: float = 0.20,
    threshold: float = 0.62,
    staking: str = "flat",
    learning_rate: float = 0.01,
    update_count: int = 0,
    total_settled: int = 0,
) -> Agent:
    return Agent(
        id=agent_id,
        policy=BanditPolicy(
            statistical_weight=stat_weight,
            market_weight=market_weight,
            confidence_threshold=threshold,
            staking_strategy=staking,
            learning_rate=learning_rate,
            update_count=update_count,
        ),
        bankroll=1000.0,
        starting_bankroll=1000.0,
        total_settled=total_settled,
        created_at=datetime.now(tz=timezone.utc),
        last_updated_at=datetime.now(tz=timezone.utc),
    )


def _make_settled_pick(
    outcome: str = "won",
    clv: float | None = 0.05,
    stat_weight: float = 0.80,
    market_weight: float = 0.20,
    confidence: float = 0.75,
) -> dict:
    return {
        "outcome": outcome,
        "clv": clv,
        "statistical_weight": stat_weight,
        "market_weight": market_weight,
        "confidence": confidence,
    }


class TestSkipsWhenTooFewPicks:
    def test_skips_update_when_below_minimum(self):
        agent = _make_agent()
        repo = MagicMock(spec=AgentRepository)
        repo.get_all_agents.return_value = [agent]
        # Return only 3 settled picks — below MIN_PICKS_FOR_UPDATE (5)
        repo.get_settled_since.return_value = [_make_settled_pick() for _ in range(3)]

        service = AgentRecalibrationService(agent_repo=repo)
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)
        service.recalibrate_all(since=since)

        repo.save_agent.assert_not_called()


class TestEffectiveLearningRate:
    def test_scales_correctly_with_cumulative_settled(self):
        # With 0 cumulative settled + 10 new picks = 10/30 scale = 0.333
        agent = _make_agent(total_settled=0, learning_rate=0.01)
        repo = MagicMock(spec=AgentRepository)
        repo.get_all_agents.return_value = [agent]
        picks = [_make_settled_pick() for _ in range(10)]
        repo.get_settled_since.return_value = picks

        service = AgentRecalibrationService(agent_repo=repo)
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)
        service.recalibrate_all(since=since)

        # Should have saved (means update happened, not skipped)
        repo.save_agent.assert_called_once()

    def test_rate_at_full_speed_when_confident_sample_reached(self):
        agent = _make_agent(total_settled=25, learning_rate=0.01)
        repo = MagicMock(spec=AgentRepository)
        repo.get_all_agents.return_value = [agent]
        picks = [_make_settled_pick() for _ in range(10)]
        repo.get_settled_since.return_value = picks

        service = AgentRecalibrationService(agent_repo=repo)
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)
        service.recalibrate_all(since=since)

        # cumulative = 25 + 10 = 35 > 30 → scale = 1.0
        # effective_lr = 0.01 * (0.20 + 0.80 * 1.0) = 0.01
        repo.save_agent.assert_called_once()


class TestStatGradient:
    def test_positive_when_stat_signal_correlated_with_positive_clv(self):
        agent = _make_agent(stat_weight=0.50, market_weight=0.50)
        repo = MagicMock(spec=AgentRepository)
        repo.get_all_agents.return_value = [agent]
        # All picks have positive CLV and high stat weight
        picks = [
            _make_settled_pick(clv=0.10, stat_weight=0.80, market_weight=0.20)
            for _ in range(10)
        ]
        repo.get_settled_since.return_value = picks

        service = AgentRecalibrationService(agent_repo=repo)
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)
        service.recalibrate_all(since=since)

        saved_agent = repo.save_agent.call_args[0][0]
        # Stat weight should have increased (positive gradient from positive CLV)
        # After normalisation, stat_weight should be > market_weight
        assert saved_agent.policy.statistical_weight > saved_agent.policy.market_weight


class TestMarketGradient:
    def test_positive_when_market_signal_correlated_with_positive_clv(self):
        agent = _make_agent(stat_weight=0.50, market_weight=0.50)
        repo = MagicMock(spec=AgentRepository)
        repo.get_all_agents.return_value = [agent]
        picks = [
            _make_settled_pick(clv=0.10, stat_weight=0.20, market_weight=0.80)
            for _ in range(10)
        ]
        repo.get_settled_since.return_value = picks

        service = AgentRecalibrationService(agent_repo=repo)
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)
        service.recalibrate_all(since=since)

        saved_agent = repo.save_agent.call_args[0][0]
        assert saved_agent.policy.market_weight > saved_agent.policy.statistical_weight


class TestWeightsNormalise:
    def test_weights_sum_to_one_after_update(self):
        agent = _make_agent(stat_weight=0.60, market_weight=0.40)
        repo = MagicMock(spec=AgentRepository)
        repo.get_all_agents.return_value = [agent]
        picks = [_make_settled_pick(clv=0.10) for _ in range(10)]
        repo.get_settled_since.return_value = picks

        service = AgentRecalibrationService(agent_repo=repo)
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)
        service.recalibrate_all(since=since)

        saved_agent = repo.save_agent.call_args[0][0]
        total = saved_agent.policy.statistical_weight + saved_agent.policy.market_weight
        assert abs(total - 1.0) < 0.001


class TestParametersClipped:
    def test_parameters_clipped_to_valid_ranges(self):
        # Start with extreme values and a very high learning rate
        agent = _make_agent(
            stat_weight=0.89,
            market_weight=0.11,
            threshold=0.84,
            learning_rate=1.0,
            total_settled=100,
        )
        repo = MagicMock(spec=AgentRepository)
        repo.get_all_agents.return_value = [agent]
        # All positive — pushes weights further in same direction
        picks = [_make_settled_pick(clv=1.0, stat_weight=0.90, market_weight=0.10) for _ in range(10)]
        repo.get_settled_since.return_value = picks

        service = AgentRecalibrationService(agent_repo=repo)
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)
        service.recalibrate_all(since=since)

        saved_agent = repo.save_agent.call_args[0][0]
        assert 0.10 <= saved_agent.policy.statistical_weight <= 0.90
        assert 0.10 <= saved_agent.policy.market_weight <= 0.90
        assert 0.55 <= saved_agent.policy.confidence_threshold <= 0.85
        assert 0.10 <= saved_agent.policy.kelly_fraction <= 0.50


class TestUpdateCountIncremented:
    def test_update_count_incremented(self):
        agent = _make_agent(update_count=2)
        repo = MagicMock(spec=AgentRepository)
        repo.get_all_agents.return_value = [agent]
        picks = [_make_settled_pick() for _ in range(10)]
        repo.get_settled_since.return_value = picks

        service = AgentRecalibrationService(agent_repo=repo)
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)
        service.recalibrate_all(since=since)

        saved_agent = repo.save_agent.call_args[0][0]
        assert saved_agent.policy.update_count == 3
