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
    stat_confidence: float | None = 0.80,
    stat_edge: float | None = 0.10,
    market_confidence: float | None = 0.70,
    market_edge: float | None = 0.05,
) -> dict:
    return {
        "outcome": outcome,
        "clv": clv,
        "statistical_weight": stat_weight,
        "market_weight": market_weight,
        "confidence": confidence,
        "stat_confidence": stat_confidence,
        "stat_edge": stat_edge,
        "market_confidence": market_confidence,
        "market_edge": market_edge,
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
        # Statistical signal was more confident on winning picks
        picks = [
            _make_settled_pick(
                clv=0.10,
                stat_confidence=0.85,
                market_confidence=0.60,
            )
            for _ in range(10)
        ]
        repo.get_settled_since.return_value = picks

        service = AgentRecalibrationService(agent_repo=repo)
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)
        service.recalibrate_all(since=since)

        saved_agent = repo.save_agent.call_args[0][0]
        # Stat weight should have increased because stat signal was more
        # confident on picks with positive reward (differential gradient)
        assert saved_agent.policy.statistical_weight > saved_agent.policy.market_weight


class TestMarketGradient:
    def test_positive_when_market_signal_correlated_with_positive_clv(self):
        agent = _make_agent(stat_weight=0.50, market_weight=0.50)
        repo = MagicMock(spec=AgentRepository)
        repo.get_all_agents.return_value = [agent]
        # Market signal was more confident on winning picks
        picks = [
            _make_settled_pick(
                clv=0.10,
                stat_confidence=0.55,
                market_confidence=0.85,
            )
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
        # All positive — stat more confident → pushes stat weight further up
        picks = [
            _make_settled_pick(
                clv=1.0,
                stat_confidence=0.95,
                market_confidence=0.40,
            )
            for _ in range(10)
        ]
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


class TestDifferentialGradient:
    """Verifies the gradient uses signal-level differential, not weight reinforcement."""

    def test_equal_signals_produce_zero_weight_gradient(self):
        """When both signals have equal confidence, no weight update should occur."""
        agent = _make_agent(stat_weight=0.50, market_weight=0.50, learning_rate=0.1)
        repo = MagicMock(spec=AgentRepository)
        repo.get_all_agents.return_value = [agent]
        # Both signals equally confident — differential is zero
        picks = [
            _make_settled_pick(
                clv=0.10,
                stat_confidence=0.80,
                market_confidence=0.80,
            )
            for _ in range(10)
        ]
        repo.get_settled_since.return_value = picks

        service = AgentRecalibrationService(agent_repo=repo)
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)
        service.recalibrate_all(since=since)

        saved_agent = repo.save_agent.call_args[0][0]
        # Weights should remain equal after normalisation
        assert abs(saved_agent.policy.statistical_weight - 0.50) < 0.01
        assert abs(saved_agent.policy.market_weight - 0.50) < 0.01

    def test_wrong_signal_penalised_on_loss(self):
        """If the stat signal was more confident on a losing bet, stat weight decreases."""
        agent = _make_agent(stat_weight=0.50, market_weight=0.50, learning_rate=0.1)
        repo = MagicMock(spec=AgentRepository)
        repo.get_all_agents.return_value = [agent]
        # Stat was more confident, but the bet lost → stat should be penalised
        picks = [
            _make_settled_pick(
                clv=-0.10,
                stat_confidence=0.90,
                market_confidence=0.50,
            )
            for _ in range(10)
        ]
        repo.get_settled_since.return_value = picks

        service = AgentRecalibrationService(agent_repo=repo)
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)
        service.recalibrate_all(since=since)

        saved_agent = repo.save_agent.call_args[0][0]
        # Stat weight should have decreased
        assert saved_agent.policy.statistical_weight < saved_agent.policy.market_weight


class TestSymmetricThresholdGradient:
    """Verifies the threshold gradient is symmetric — rewards winners, penalises losers."""

    def test_winners_decrease_threshold(self):
        """Winning picks should push threshold down (be less conservative)."""
        agent = _make_agent(threshold=0.70, learning_rate=0.1)
        repo = MagicMock(spec=AgentRepository)
        repo.get_all_agents.return_value = [agent]
        picks = [
            _make_settled_pick(clv=0.10)
            for _ in range(10)
        ]
        repo.get_settled_since.return_value = picks

        service = AgentRecalibrationService(agent_repo=repo)
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)
        service.recalibrate_all(since=since)

        saved_agent = repo.save_agent.call_args[0][0]
        # All winners → threshold should decrease from 0.70
        assert saved_agent.policy.confidence_threshold < 0.70

    def test_losers_increase_threshold(self):
        """Losing picks should push threshold up (be more conservative)."""
        agent = _make_agent(threshold=0.62, learning_rate=0.1)
        repo = MagicMock(spec=AgentRepository)
        repo.get_all_agents.return_value = [agent]
        picks = [
            _make_settled_pick(clv=-0.10)
            for _ in range(10)
        ]
        repo.get_settled_since.return_value = picks

        service = AgentRecalibrationService(agent_repo=repo)
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)
        service.recalibrate_all(since=since)

        saved_agent = repo.save_agent.call_args[0][0]
        # All losers → threshold should increase from 0.62
        assert saved_agent.policy.confidence_threshold > 0.62

    def test_balanced_outcomes_stable_threshold(self):
        """Equal wins and losses should leave threshold roughly unchanged."""
        agent = _make_agent(threshold=0.65, learning_rate=0.1)
        repo = MagicMock(spec=AgentRepository)
        repo.get_all_agents.return_value = [agent]
        # 5 winners, 5 losers with equal magnitude
        picks = (
            [_make_settled_pick(clv=0.10) for _ in range(5)]
            + [_make_settled_pick(clv=-0.10) for _ in range(5)]
        )
        repo.get_settled_since.return_value = picks

        service = AgentRecalibrationService(agent_repo=repo)
        since = datetime.now(tz=timezone.utc) - timedelta(days=7)
        service.recalibrate_all(since=since)

        saved_agent = repo.save_agent.call_args[0][0]
        # Net gradient is zero → threshold should remain close to 0.65
        assert abs(saved_agent.policy.confidence_threshold - 0.65) < 0.01
