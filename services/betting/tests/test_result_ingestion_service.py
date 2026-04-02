"""Tests for ResultIngestionService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from betting.adapters.odds_api import OddsApiProvider
from betting.config.market_config import MarketConfigLoader
from betting.interfaces.ledger_repository import ILedgerRepository
from betting.services.result_ingestion_service import ResultIngestionService, SettlementSummary


def _make_service(
    pending_picks: list[dict] | None = None,
    fetch_results_side_effect=None,
    settlement_lag_hours: int = 12,
) -> tuple[ResultIngestionService, MagicMock, MagicMock]:
    odds_api = MagicMock(spec=OddsApiProvider)
    ledger = MagicMock(spec=ILedgerRepository)

    if pending_picks is not None:
        ledger.get_pending_picks.return_value = pending_picks
    else:
        ledger.get_pending_picks.return_value = []

    if fetch_results_side_effect is not None:
        odds_api.fetch_results.side_effect = fetch_results_side_effect

    market_loader = MarketConfigLoader()
    service = ResultIngestionService(
        odds_api=odds_api,
        ledger_repo=ledger,
        market_loader=market_loader,
        settlement_lag_hours=settlement_lag_hours,
    )
    return service, odds_api, ledger


def _past_kickoff(hours_ago: int = 24) -> str:
    return (datetime.now(tz=timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def _future_kickoff(hours_ahead: int = 2) -> str:
    return (datetime.now(tz=timezone.utc) + timedelta(hours=hours_ahead)).isoformat()


def _make_pick(
    pick_id: str = "pick-001",
    home_team: str = "Arsenal",
    away_team: str = "Chelsea",
    selection: str = "1X",
    kickoff: str | None = None,
    market: str = "double_chance",
) -> dict:
    return {
        "id": pick_id,
        "home_team": home_team,
        "away_team": away_team,
        "selection": selection,
        "market": market,
        "kickoff": kickoff or _past_kickoff(24),
        "outcome": None,
    }


# --- _determine_outcome tests ---

class TestDetermineOutcome:
    def _service(self) -> ResultIngestionService:
        service, _, _ = _make_service()
        return service

    def test_1x_wins_on_home(self):
        s = self._service()
        assert s._determine_outcome("1X", "double_chance", {"ftr": "H"}) == "won"

    def test_1x_wins_on_draw(self):
        s = self._service()
        assert s._determine_outcome("1X", "double_chance", {"ftr": "D"}) == "won"

    def test_1x_loses_on_away(self):
        s = self._service()
        assert s._determine_outcome("1X", "double_chance", {"ftr": "A"}) == "lost"

    def test_12_wins_on_home(self):
        s = self._service()
        assert s._determine_outcome("12", "double_chance", {"ftr": "H"}) == "won"

    def test_12_wins_on_away(self):
        s = self._service()
        assert s._determine_outcome("12", "double_chance", {"ftr": "A"}) == "won"

    def test_12_loses_on_draw(self):
        s = self._service()
        assert s._determine_outcome("12", "double_chance", {"ftr": "D"}) == "lost"

    def test_x2_wins_on_draw(self):
        s = self._service()
        assert s._determine_outcome("X2", "double_chance", {"ftr": "D"}) == "won"

    def test_x2_wins_on_away(self):
        s = self._service()
        assert s._determine_outcome("X2", "double_chance", {"ftr": "A"}) == "won"

    def test_x2_loses_on_home(self):
        s = self._service()
        assert s._determine_outcome("X2", "double_chance", {"ftr": "H"}) == "lost"

    def test_unknown_selection_returns_void(self):
        s = self._service()
        assert s._determine_outcome("UNKNOWN", "double_chance", {"ftr": "H"}) == "void"

    def test_empty_ftr_returns_void(self):
        s = self._service()
        assert s._determine_outcome("1X", "double_chance", {"ftr": ""}) == "void"

    def test_missing_ftr_returns_void(self):
        s = self._service()
        assert s._determine_outcome("1X", "double_chance", {}) == "void"


# --- _ftr_from_scores tests ---

class TestFtrFromScores:
    def _service(self) -> ResultIngestionService:
        service, _, _ = _make_service()
        return service

    def test_home_win(self):
        s = self._service()
        event = {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "scores": [
                {"name": "Arsenal", "score": "2"},
                {"name": "Chelsea", "score": "1"},
            ],
        }
        assert s._ftr_from_scores(event) == "H"

    def test_away_win(self):
        s = self._service()
        event = {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "scores": [
                {"name": "Arsenal", "score": "0"},
                {"name": "Chelsea", "score": "3"},
            ],
        }
        assert s._ftr_from_scores(event) == "A"

    def test_draw(self):
        s = self._service()
        event = {
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "scores": [
                {"name": "Arsenal", "score": "1"},
                {"name": "Chelsea", "score": "1"},
            ],
        }
        assert s._ftr_from_scores(event) == "D"


# --- settle_pending_picks tests ---

class TestSettlePendingPicks:
    def test_no_pending_picks_returns_empty_summary(self):
        service, _, _ = _make_service(pending_picks=[])
        summary = service.settle_pending_picks(["PL"])
        assert summary.settled == 0
        assert summary.still_pending == 0

    def test_pick_within_settlement_lag_stays_pending(self):
        # Kickoff only 1 hour ago — within 12-hour lag
        pick = _make_pick(kickoff=_past_kickoff(hours_ago=1))
        service, odds_api, ledger = _make_service(
            pending_picks=[pick],
            settlement_lag_hours=12,
        )
        odds_api.fetch_results.return_value = []
        summary = service.settle_pending_picks(["PL"])
        assert summary.still_pending == 1
        assert summary.settled == 0
        ledger.settle_pick.assert_not_called()

    def test_pick_with_no_api_result_stays_pending(self):
        pick = _make_pick(kickoff=_past_kickoff(hours_ago=24))
        service, odds_api, ledger = _make_service(pending_picks=[pick])
        odds_api.fetch_results.return_value = []
        summary = service.settle_pending_picks(["PL"])
        assert summary.still_pending == 1
        assert summary.settled == 0
        ledger.settle_pick.assert_not_called()

    def test_won_pick_settled_correctly(self):
        pick = _make_pick(selection="1X", kickoff=_past_kickoff(24))
        service, odds_api, ledger = _make_service(pending_picks=[pick])
        odds_api.fetch_results.return_value = [
            {
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "completed": True,
                "scores": [
                    {"name": "Arsenal", "score": "2"},
                    {"name": "Chelsea", "score": "1"},
                ],
            }
        ]
        summary = service.settle_pending_picks(["PL"])
        assert summary.settled == 1
        assert summary.won == 1
        assert summary.lost == 0
        ledger.settle_pick.assert_called_once_with("pick-001", "won")

    def test_lost_pick_settled_correctly(self):
        pick = _make_pick(selection="1X", kickoff=_past_kickoff(24))
        service, odds_api, ledger = _make_service(pending_picks=[pick])
        odds_api.fetch_results.return_value = [
            {
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "completed": True,
                "scores": [
                    {"name": "Arsenal", "score": "0"},
                    {"name": "Chelsea", "score": "2"},
                ],
            }
        ]
        summary = service.settle_pending_picks(["PL"])
        assert summary.settled == 1
        assert summary.lost == 1
        assert summary.won == 0
        ledger.settle_pick.assert_called_once_with("pick-001", "lost")

    def test_failed_league_fetch_logs_error_and_continues(self):
        pick = _make_pick(home_team="Real Madrid", away_team="Barcelona", kickoff=_past_kickoff(24))
        service, odds_api, ledger = _make_service(pending_picks=[pick])

        def side_effect(league, days_from=2):
            if league == "PL":
                raise RuntimeError("API error")
            return []

        odds_api.fetch_results.side_effect = side_effect

        # Should not raise — error is logged and other leagues continue
        summary = service.settle_pending_picks(["PL", "LL"])
        assert summary.still_pending == 1

    def test_kickoff_without_timezone_treated_as_utc(self):
        # Kickoff without tzinfo — should be treated as UTC
        naive_kickoff = (datetime.now(tz=timezone.utc) - timedelta(hours=24)).replace(tzinfo=None).isoformat()
        pick = _make_pick(kickoff=naive_kickoff)
        service, odds_api, ledger = _make_service(pending_picks=[pick])
        odds_api.fetch_results.return_value = [
            {
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "completed": True,
                "scores": [
                    {"name": "Arsenal", "score": "1"},
                    {"name": "Chelsea", "score": "1"},
                ],
            }
        ]
        summary = service.settle_pending_picks(["PL"])
        assert summary.settled == 1
