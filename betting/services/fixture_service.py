import logging
from datetime import datetime, timezone, timedelta

from betting.interfaces.fixture_provider import IFixtureProvider
from betting.interfaces.odds_provider import IOddsProvider
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot

logger = logging.getLogger(__name__)

# Known international break windows (start, end) — UTC dates only, times ignored.
# Extend this list or extract to config as more seasons are tracked.
_INTERNATIONAL_BREAKS: list[tuple[datetime, datetime]] = [
    # 2024/25 season examples
    (datetime(2024, 10, 7, tzinfo=timezone.utc), datetime(2024, 10, 15, tzinfo=timezone.utc)),
    (datetime(2024, 11, 11, tzinfo=timezone.utc), datetime(2024, 11, 19, tzinfo=timezone.utc)),
    (datetime(2025, 3, 17, tzinfo=timezone.utc), datetime(2025, 3, 25, tzinfo=timezone.utc)),
]


class FixtureService:
    def __init__(
        self,
        fixture_provider: IFixtureProvider,
        odds_provider: IOddsProvider,
        supported_leagues: list[str],
        min_lead_hours: int = 2,
        max_lead_hours: int = 48,
    ) -> None:
        self._fixture_provider = fixture_provider
        self._odds_provider = odds_provider
        self._supported_leagues = supported_leagues
        self._min_lead_hours = min_lead_hours
        self._max_lead_hours = max_lead_hours

    def get_eligible_fixtures(
        self,
        markets: list[str],
    ) -> list[tuple[Fixture, OddsSnapshot]]:
        """
        Returns (fixture, odds) pairs that pass all eligibility checks.
        Filters applied in order:
          1. League in supported_leagues
          2. Kickoff within [min_lead_hours, max_lead_hours] window
          3. Not during an international break
          4. Odds snapshot available for requested markets
        """
        now = datetime.now(tz=timezone.utc)
        earliest = now + timedelta(hours=self._min_lead_hours)
        latest = now + timedelta(hours=self._max_lead_hours)

        raw: list[Fixture] = self._fixture_provider.fetch_upcoming(
            leagues=self._supported_leagues,
            days_ahead=self._max_lead_hours // 24 + 1,
        )

        results: list[tuple[Fixture, OddsSnapshot]] = []
        for fixture in raw:
            # 1. League filter
            if fixture.league not in self._supported_leagues:
                logger.debug("Fixture %s filtered: league %r not supported", fixture.id, fixture.league)
                continue

            kickoff = fixture.kickoff
            # Ensure kickoff is timezone-aware for comparison
            if kickoff.tzinfo is None:
                kickoff = kickoff.replace(tzinfo=timezone.utc)

            # 2. Lead-time window
            if not (earliest <= kickoff <= latest):
                logger.debug(
                    "Fixture %s filtered: kickoff %s outside lead-time window",
                    fixture.id,
                    kickoff.isoformat(),
                )
                continue

            # 3. International break
            if self._is_international_break(kickoff):
                logger.debug("Fixture %s filtered: international break", fixture.id)
                continue

            # 4. Odds availability
            odds = self._odds_provider.fetch_odds(fixture, markets)
            if odds is None:
                logger.debug("Fixture %s filtered: no odds available", fixture.id)
                continue

            results.append((fixture, odds))

        logger.info("Total eligible fixtures: %d", len(results))
        return results

    def _is_international_break(self, kickoff: datetime) -> bool:
        for start, end in _INTERNATIONAL_BREAKS:
            if start <= kickoff <= end:
                return True
        return False
