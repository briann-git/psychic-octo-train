from datetime import datetime, timezone

from betting.interfaces.odds_provider import IOddsProvider
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot


class OddsApiProvider(IOddsProvider):
    """Stub implementation — returns hard-coded odds for spine verification."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def fetch_odds(
        self,
        fixture: Fixture,
        markets: list[str],
    ) -> OddsSnapshot | None:
        return OddsSnapshot(
            fixture_id=fixture.id,
            market="double_chance",
            bookmaker="stub",
            home_draw=1.40,   # 1X
            home_away=1.25,   # 12
            draw_away=2.10,   # X2
            fetched_at=datetime.now(tz=timezone.utc),
        )
