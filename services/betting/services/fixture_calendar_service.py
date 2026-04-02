"""Service for managing the local fixture calendar."""

import logging
from datetime import datetime, timedelta, timezone

from betting.interfaces.fixture_provider import IFixtureProvider
from betting.interfaces.ledger_repository import ILedgerRepository
from betting.models.fixture import Fixture

logger = logging.getLogger(__name__)


class FixtureCalendarService:
    def __init__(
        self,
        fixture_provider: IFixtureProvider,
        ledger_repo: ILedgerRepository,
        lookahead_days: int = 7,
    ) -> None:
        self._fixture_provider = fixture_provider
        self._ledger = ledger_repo
        self._lookahead_days = lookahead_days

    def refresh(self, leagues: list[str]) -> int:
        """
        Fetches upcoming fixtures from the Odds API for all active leagues
        and persists them to the local calendar.
        Returns the number of fixtures stored.
        Called once per week by the weekly fetch job.
        Logs per-league success/failure — does not raise on partial failure.
        """
        all_fixtures: list[Fixture] = []
        for league in leagues:
            try:
                fixtures = self._fixture_provider.fetch_upcoming(
                    leagues=[league],
                    days_ahead=self._lookahead_days,
                )
                all_fixtures.extend(fixtures)
                logger.info(
                    "Fetched %d fixture(s) for %s", len(fixtures), league
                )
            except Exception as exc:
                logger.error(
                    "Failed to fetch calendar for %s: %s", league, exc
                )

        if all_fixtures:
            self._ledger.upsert_fixture_calendar(all_fixtures)

        logger.info(
            "Calendar refresh complete — %d fixture(s) stored", len(all_fixtures)
        )
        return len(all_fixtures)

    def has_fixtures_today(
        self,
        leagues: list[str],
        min_lead_hours: int = 2,
        max_lead_hours: int = 48,
    ) -> bool:
        """
        Returns True if the local calendar contains any fixtures
        within the current analysis window.
        No API calls — reads from SQLite only.
        """
        now = datetime.now(tz=timezone.utc)
        from_dt = now + timedelta(hours=min_lead_hours)
        to_dt = now + timedelta(hours=max_lead_hours)

        fixtures = self._ledger.get_calendar_fixtures(
            from_dt=from_dt,
            to_dt=to_dt,
            leagues=leagues,
        )
        return len(fixtures) > 0

    def upcoming_fixture_dates(
        self, leagues: list[str]
    ) -> list[str]:
        """
        Returns a sorted list of unique dates (YYYY-MM-DD UTC) that have
        fixtures in the calendar. Useful for logging what's coming up.
        """
        now = datetime.now(tz=timezone.utc)
        to_dt = now + timedelta(days=self._lookahead_days)
        fixtures = self._ledger.get_calendar_fixtures(
            from_dt=now, to_dt=to_dt, leagues=leagues
        )
        dates = sorted({f["kickoff"][:10] for f in fixtures})
        return dates
