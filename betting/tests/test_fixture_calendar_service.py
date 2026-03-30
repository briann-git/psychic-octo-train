"""Tests for FixtureCalendarService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from betting.interfaces.fixture_provider import IFixtureProvider
from betting.interfaces.ledger_repository import ILedgerRepository
from betting.models.fixture import Fixture
from betting.services.fixture_calendar_service import FixtureCalendarService


def _make_fixture(
    fixture_id: str = "fix-001",
    home_team: str = "Arsenal",
    away_team: str = "Chelsea",
    league: str = "PL",
    season: str = "2024/25",
    hours_ahead: int = 24,
) -> Fixture:
    return Fixture(
        id=fixture_id,
        home_team=home_team,
        away_team=away_team,
        league=league,
        season=season,
        matchday=30,
        kickoff=datetime.now(tz=timezone.utc) + timedelta(hours=hours_ahead),
    )


def _make_service(
    fetch_upcoming_side_effect=None,
    get_calendar_fixtures_return=None,
    lookahead_days: int = 7,
) -> tuple[FixtureCalendarService, MagicMock, MagicMock]:
    provider = MagicMock(spec=IFixtureProvider)
    ledger = MagicMock(spec=ILedgerRepository)

    if fetch_upcoming_side_effect is not None:
        provider.fetch_upcoming.side_effect = fetch_upcoming_side_effect

    if get_calendar_fixtures_return is not None:
        ledger.get_calendar_fixtures.return_value = get_calendar_fixtures_return
    else:
        ledger.get_calendar_fixtures.return_value = []

    service = FixtureCalendarService(
        fixture_provider=provider,
        ledger_repo=ledger,
        lookahead_days=lookahead_days,
    )
    return service, provider, ledger


class TestRefresh:
    def test_fetches_fixtures_per_league_and_stores_all(self):
        fix_pl = _make_fixture(fixture_id="fix-pl", league="PL")
        fix_la = _make_fixture(fixture_id="fix-la", league="LaLiga")

        service, provider, ledger = _make_service(
            fetch_upcoming_side_effect=[[fix_pl], [fix_la]],
        )

        count = service.refresh(["PL", "LaLiga"])

        assert count == 2
        assert provider.fetch_upcoming.call_count == 2
        provider.fetch_upcoming.assert_any_call(leagues=["PL"], days_ahead=7)
        provider.fetch_upcoming.assert_any_call(leagues=["LaLiga"], days_ahead=7)
        ledger.upsert_fixture_calendar.assert_called_once_with([fix_pl, fix_la])

    def test_logs_error_and_continues_on_per_league_failure(self):
        fix_la = _make_fixture(fixture_id="fix-la", league="LaLiga")

        service, provider, ledger = _make_service(
            fetch_upcoming_side_effect=[
                RuntimeError("API down"),
                [fix_la],
            ],
        )

        count = service.refresh(["PL", "LaLiga"])

        assert count == 1
        ledger.upsert_fixture_calendar.assert_called_once_with([fix_la])

    def test_does_not_upsert_when_all_leagues_fail(self):
        service, provider, ledger = _make_service(
            fetch_upcoming_side_effect=[RuntimeError("API down")],
        )

        count = service.refresh(["PL"])

        assert count == 0
        ledger.upsert_fixture_calendar.assert_not_called()

    def test_uses_configured_lookahead_days(self):
        service, provider, ledger = _make_service(
            fetch_upcoming_side_effect=[[]],
            lookahead_days=14,
        )

        service.refresh(["PL"])

        provider.fetch_upcoming.assert_called_once_with(leagues=["PL"], days_ahead=14)


class TestHasFixturesToday:
    def test_returns_true_when_fixtures_in_window(self):
        service, _, ledger = _make_service(
            get_calendar_fixtures_return=[{"id": "fix-001", "kickoff": "2025-04-01T15:00:00+00:00"}],
        )

        result = service.has_fixtures_today(leagues=["PL"])

        assert result is True
        ledger.get_calendar_fixtures.assert_called_once()

    def test_returns_false_when_calendar_is_empty(self):
        service, _, _ = _make_service(
            get_calendar_fixtures_return=[],
        )

        result = service.has_fixtures_today(leagues=["PL"])

        assert result is False

    def test_returns_false_when_all_fixtures_outside_window(self):
        service, _, _ = _make_service(
            get_calendar_fixtures_return=[],
        )

        result = service.has_fixtures_today(
            leagues=["PL"], min_lead_hours=2, max_lead_hours=48
        )

        assert result is False

    def test_passes_correct_leagues(self):
        service, _, ledger = _make_service(
            get_calendar_fixtures_return=[],
        )

        service.has_fixtures_today(leagues=["PL", "LaLiga"])

        call_kwargs = ledger.get_calendar_fixtures.call_args
        assert call_kwargs.kwargs["leagues"] == ["PL", "LaLiga"]

    def test_uses_min_and_max_lead_hours(self):
        service, _, ledger = _make_service(
            get_calendar_fixtures_return=[],
        )

        service.has_fixtures_today(
            leagues=["PL"], min_lead_hours=4, max_lead_hours=72
        )

        call_kwargs = ledger.get_calendar_fixtures.call_args
        from_dt = call_kwargs.kwargs["from_dt"]
        to_dt = call_kwargs.kwargs["to_dt"]
        # The window should be approximately min_lead_hours to max_lead_hours from now
        diff_hours = (to_dt - from_dt).total_seconds() / 3600
        assert abs(diff_hours - (72 - 4)) < 0.1


class TestUpcomingFixtureDates:
    def test_returns_sorted_unique_dates(self):
        service, _, ledger = _make_service(
            get_calendar_fixtures_return=[
                {"kickoff": "2025-04-03T15:00:00+00:00"},
                {"kickoff": "2025-04-01T20:00:00+00:00"},
                {"kickoff": "2025-04-01T15:00:00+00:00"},
                {"kickoff": "2025-04-03T18:00:00+00:00"},
            ],
        )

        dates = service.upcoming_fixture_dates(leagues=["PL"])

        assert dates == ["2025-04-01", "2025-04-03"]

    def test_returns_empty_list_when_no_fixtures(self):
        service, _, _ = _make_service(
            get_calendar_fixtures_return=[],
        )

        dates = service.upcoming_fixture_dates(leagues=["PL"])

        assert dates == []
