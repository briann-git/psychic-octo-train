"""Tests for fixture_calendar table in SqliteLedgerRepository."""

from datetime import datetime, timedelta, timezone

import pytest

from betting.adapters.sqlite_ledger import SqliteLedgerRepository
from betting.models.fixture import Fixture


@pytest.fixture()
def repo(tmp_path):
    db_path = str(tmp_path / "test_ledger.db")
    return SqliteLedgerRepository(db_path=db_path)


def _make_fixture(
    fixture_id: str = "fix-001",
    home_team: str = "Arsenal",
    away_team: str = "Chelsea",
    league: str = "PL",
    season: str = "2024/25",
    kickoff: datetime | None = None,
) -> Fixture:
    if kickoff is None:
        kickoff = datetime.now(tz=timezone.utc) + timedelta(hours=24)
    return Fixture(
        id=fixture_id,
        home_team=home_team,
        away_team=away_team,
        league=league,
        season=season,
        matchday=30,
        kickoff=kickoff,
    )


class TestUpsertFixtureCalendar:
    def test_inserts_fixtures_correctly(self, repo):
        fixtures = [
            _make_fixture(fixture_id="fix-001"),
            _make_fixture(fixture_id="fix-002", home_team="Liverpool", away_team="Man City"),
        ]
        repo.upsert_fixture_calendar(fixtures)

        now = datetime.now(tz=timezone.utc)
        results = repo.get_calendar_fixtures(
            from_dt=now, to_dt=now + timedelta(days=7)
        )
        assert len(results) == 2
        ids = {r["id"] for r in results}
        assert ids == {"fix-001", "fix-002"}

    def test_replaces_existing_row_for_same_fixture_id(self, repo):
        fixture_v1 = _make_fixture(fixture_id="fix-001", home_team="Arsenal")
        repo.upsert_fixture_calendar([fixture_v1])

        fixture_v2 = _make_fixture(fixture_id="fix-001", home_team="Updated Arsenal")
        repo.upsert_fixture_calendar([fixture_v2])

        now = datetime.now(tz=timezone.utc)
        results = repo.get_calendar_fixtures(
            from_dt=now, to_dt=now + timedelta(days=7)
        )
        assert len(results) == 1
        assert results[0]["home_team"] == "Updated Arsenal"

    def test_prunes_past_fixtures(self, repo):
        past_fixture = _make_fixture(
            fixture_id="fix-past",
            kickoff=datetime.now(tz=timezone.utc) - timedelta(hours=2),
        )
        future_fixture = _make_fixture(
            fixture_id="fix-future",
            kickoff=datetime.now(tz=timezone.utc) + timedelta(hours=24),
        )
        # First insert the past fixture directly
        repo.upsert_fixture_calendar([past_fixture, future_fixture])

        # The upsert prunes past fixtures, so only the future one remains
        # But since the past fixture's kickoff < now, it gets pruned
        # We need to verify by inserting a new batch which triggers pruning
        new_fixture = _make_fixture(
            fixture_id="fix-new",
            kickoff=datetime.now(tz=timezone.utc) + timedelta(hours=48),
        )
        repo.upsert_fixture_calendar([new_fixture])

        now = datetime.now(tz=timezone.utc)
        results = repo.get_calendar_fixtures(
            from_dt=now - timedelta(days=1),
            to_dt=now + timedelta(days=7),
        )
        ids = {r["id"] for r in results}
        assert "fix-past" not in ids
        assert "fix-future" in ids
        assert "fix-new" in ids


class TestGetCalendarFixtures:
    def test_returns_fixtures_within_window(self, repo):
        now = datetime.now(tz=timezone.utc)
        in_window = _make_fixture(
            fixture_id="fix-in", kickoff=now + timedelta(hours=24)
        )
        before_window = _make_fixture(
            fixture_id="fix-before", kickoff=now + timedelta(hours=1)
        )
        after_window = _make_fixture(
            fixture_id="fix-after", kickoff=now + timedelta(hours=72)
        )
        repo.upsert_fixture_calendar([in_window, before_window, after_window])

        results = repo.get_calendar_fixtures(
            from_dt=now + timedelta(hours=2),
            to_dt=now + timedelta(hours=48),
        )
        ids = {r["id"] for r in results}
        assert "fix-in" in ids
        assert "fix-before" not in ids
        assert "fix-after" not in ids

    def test_filters_by_league(self, repo):
        now = datetime.now(tz=timezone.utc)
        pl_fixture = _make_fixture(fixture_id="fix-pl", league="PL")
        la_fixture = _make_fixture(fixture_id="fix-la", league="LaLiga")
        repo.upsert_fixture_calendar([pl_fixture, la_fixture])

        results = repo.get_calendar_fixtures(
            from_dt=now,
            to_dt=now + timedelta(days=7),
            leagues=["PL"],
        )
        assert len(results) == 1
        assert results[0]["league"] == "PL"

    def test_returns_empty_list_when_no_fixtures_in_window(self, repo):
        now = datetime.now(tz=timezone.utc)
        far_future = _make_fixture(
            fixture_id="fix-far", kickoff=now + timedelta(days=30)
        )
        repo.upsert_fixture_calendar([far_future])

        results = repo.get_calendar_fixtures(
            from_dt=now,
            to_dt=now + timedelta(hours=48),
        )
        assert results == []

    def test_returns_all_leagues_when_none_specified(self, repo):
        now = datetime.now(tz=timezone.utc)
        repo.upsert_fixture_calendar([
            _make_fixture(fixture_id="fix-pl", league="PL"),
            _make_fixture(fixture_id="fix-la", league="LaLiga"),
        ])

        results = repo.get_calendar_fixtures(
            from_dt=now,
            to_dt=now + timedelta(days=7),
            leagues=None,
        )
        assert len(results) == 2

    def test_results_ordered_by_kickoff_asc(self, repo):
        now = datetime.now(tz=timezone.utc)
        later = _make_fixture(
            fixture_id="fix-later", kickoff=now + timedelta(hours=48)
        )
        earlier = _make_fixture(
            fixture_id="fix-earlier", kickoff=now + timedelta(hours=12)
        )
        repo.upsert_fixture_calendar([later, earlier])

        results = repo.get_calendar_fixtures(
            from_dt=now,
            to_dt=now + timedelta(days=7),
        )
        assert results[0]["id"] == "fix-earlier"
        assert results[1]["id"] == "fix-later"
