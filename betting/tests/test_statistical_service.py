"""Tests for StatisticalService."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from betting.interfaces.stats_provider import IStatsProvider
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot
from betting.services.statistical_service import StatisticalService


def _make_fixture() -> Fixture:
    return Fixture(
        id="fix-001",
        home_team="Arsenal",
        away_team="Chelsea",
        league="PL",
        season="2024/25",
        matchday=30,
        kickoff=datetime(2025, 4, 1, 15, 0, tzinfo=timezone.utc),
    )


def _make_odds(home_draw: float = 1.40, home_away: float = 1.25, draw_away: float = 2.10) -> OddsSnapshot:
    return OddsSnapshot(
        fixture_id="fix-001",
        market="double_chance",
        bookmaker="stub",
        selections={"1X": home_draw, "12": home_away, "X2": draw_away},
        fetched_at=datetime.now(tz=timezone.utc),
    )


def _make_service(
    home_attack: float = 1.2,
    home_defence: float = 0.9,
    away_attack: float = 1.0,
    away_defence: float = 1.0,
    league_avg_home: float = 1.5,
    league_avg_away: float = 1.2,
) -> StatisticalService:
    provider = MagicMock(spec=IStatsProvider)
    provider.get_attack_defence_ratings.return_value = (
        home_attack, home_defence, away_attack, away_defence
    )
    provider.get_league_averages.return_value = (league_avg_home, league_avg_away)
    from betting.config.market_config import MarketConfigLoader
    return StatisticalService(stats_provider=provider, market_loader=MarketConfigLoader())


class TestExpectedGoals:
    def test_neutral_teams_returns_league_averages(self):
        svc = _make_service(
            home_attack=1.0, home_defence=1.0,
            away_attack=1.0, away_defence=1.0,
            league_avg_home=1.5, league_avg_away=1.2,
        )
        home_xg, away_xg = svc._expected_goals(1.0, 1.0, 1.0, 1.0, 1.5, 1.2)
        assert home_xg == pytest.approx(1.5)
        assert away_xg == pytest.approx(1.2)

    def test_strong_home_attack_increases_home_xg(self):
        home_xg, away_xg = StatisticalService._expected_goals(1.5, 1.0, 1.0, 1.0, 1.5, 1.2)
        assert home_xg > 1.5
        assert away_xg == pytest.approx(1.2)

    def test_weak_away_defence_increases_home_xg(self):
        # away_defence > 1 means they concede more
        home_xg, _ = StatisticalService._expected_goals(1.0, 1.0, 1.0, 1.3, 1.5, 1.2)
        assert home_xg == pytest.approx(1.0 * 1.3 * 1.5)


class TestScoreMatrix:
    def test_probabilities_sum_close_to_one(self):
        matrix = StatisticalService._score_matrix(1.5, 1.2)
        total = sum(matrix.values())
        assert total == pytest.approx(1.0, abs=0.01)

    def test_matrix_has_correct_size(self):
        matrix = StatisticalService._score_matrix(1.5, 1.2, max_goals=4)
        assert len(matrix) == 5 * 5  # (0..4) x (0..4)

    def test_all_probabilities_non_negative(self):
        matrix = StatisticalService._score_matrix(1.5, 1.2)
        assert all(p >= 0.0 for p in matrix.values())


class TestAnalyse:
    def test_returns_signal_with_correct_fixture_id(self):
        svc = _make_service()
        signal = svc.analyse(_make_fixture(), _make_odds())
        assert signal.fixture_id == "fix-001"
        assert signal.agent_id == "statistical"

    def test_recommendation_is_valid(self):
        svc = _make_service()
        signal = svc.analyse(_make_fixture(), _make_odds())
        assert signal.recommendation in ("back", "lay", "skip")

    def test_selection_is_valid_double_chance(self):
        svc = _make_service()
        signal = svc.analyse(_make_fixture(), _make_odds())
        assert signal.selection in ("1X", "12", "X2")

    def test_confidence_between_zero_and_one(self):
        svc = _make_service()
        signal = svc.analyse(_make_fixture(), _make_odds())
        assert 0.0 <= signal.confidence <= 1.0

    def test_back_when_positive_edge(self):
        # Make odds very generous (implied prob low) so model has edge
        odds = _make_odds(home_draw=2.0, home_away=2.0, draw_away=2.0)
        svc = _make_service()
        signal = svc.analyse(_make_fixture(), odds)
        assert signal.recommendation == "back"
        assert signal.edge > 0

    def test_skip_when_no_edge(self):
        # Very tight odds (implied prob ~1 each) → no edge
        odds = _make_odds(home_draw=1.01, home_away=1.01, draw_away=1.01)
        svc = _make_service()
        signal = svc.analyse(_make_fixture(), odds)
        assert signal.recommendation == "skip"
        assert signal.edge <= 0

    def test_reasoning_contains_xg_info(self):
        svc = _make_service()
        signal = svc.analyse(_make_fixture(), _make_odds())
        assert "home_xg" in signal.reasoning
        assert "away_xg" in signal.reasoning
