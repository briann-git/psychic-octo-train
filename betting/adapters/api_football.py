from datetime import datetime, timezone, timedelta

from betting.interfaces.fixture_provider import IFixtureProvider
from betting.models.fixture import Fixture


class ApiFootballProvider(IFixtureProvider):
    """Stub implementation — returns hard-coded fixtures for spine verification."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def fetch_upcoming(
        self,
        leagues: list[str],
        days_ahead: int = 2,
    ) -> list[Fixture]:
        now = datetime.now(tz=timezone.utc)
        return [
            Fixture(
                id="stub-fixture-001",
                home_team="Arsenal",
                away_team="Chelsea",
                league="PL",
                season="2024/25",
                matchday=30,
                kickoff=now + timedelta(hours=24),
                venue="Emirates Stadium",
            )
        ]
