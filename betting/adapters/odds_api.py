import logging
from datetime import datetime, timezone

import httpx

from betting.config.league_config import LeagueConfigLoader
from betting.interfaces.fixture_provider import IFixtureProvider
from betting.interfaces.odds_provider import IOddsProvider
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot
from betting.utils import season_from_date

logger = logging.getLogger(__name__)

PREFERRED_BOOKMAKERS: list[str] = ["bet365", "williamhill", "betfair_ex_eu"]


class OddsApiProvider(IFixtureProvider, IOddsProvider):
    """Real implementation backed by The Odds API (https://api.the-odds-api.com)."""

    def __init__(
        self,
        api_key: str,
        league_loader: LeagueConfigLoader | None = None,
    ) -> None:
        self._api_key = api_key
        self._league_loader = league_loader or LeagueConfigLoader()
        self._cache: dict[str, list[dict]] = {}

    # ------------------------------------------------------------------
    # IFixtureProvider
    # ------------------------------------------------------------------

    def fetch_upcoming(self, leagues: list[str], days_ahead: int = 2) -> list[Fixture]:
        results: list[Fixture] = []
        for league in leagues:
            sport_key = self._league_loader.odds_api_key(league)
            if sport_key is None:
                logger.warning("League %r not in config — skipping", league)
                continue
            events = self._fetch_events(sport_key)
            for event in events:
                results.append(self._to_fixture(event, league))
        return results

    # ------------------------------------------------------------------
    # IOddsProvider
    # ------------------------------------------------------------------

    def fetch_odds(self, fixture: Fixture, markets: list[str]) -> OddsSnapshot | None:
        sport_key = self._league_loader.odds_api_key(fixture.league)
        if sport_key is None:
            logger.warning("League %r not in config — cannot fetch odds", fixture.league)
            return None
        events = self._fetch_events(sport_key)
        for event in events:
            if event["id"] == fixture.id:
                return self._to_odds_snapshot(event, fixture.id)
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_events(self, sport_key: str) -> list[dict]:
        if sport_key in self._cache:
            logger.info("Cache hit for sport key %r", sport_key)
            return self._cache[sport_key]

        logger.info("Fetching events for sport key %r", sport_key)
        try:
            response = httpx.get(
                f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds",
                params={
                    "apiKey": self._api_key,
                    "regions": "eu",
                    "markets": "h2h",
                    "oddsFormat": "decimal",
                },
                timeout=10,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "HTTP error from Odds API — status %s, url %s",
                exc.response.status_code,
                exc.request.url,
            )
            raise

        events: list[dict] = response.json()
        self._cache[sport_key] = events
        return events

    def _to_fixture(self, event: dict, league: str) -> Fixture:
        return Fixture(
            id=event["id"],
            home_team=event["home_team"],
            away_team=event["away_team"],
            league=league,
            season=season_from_date(
                datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00"))
            ),
            matchday=0,
            kickoff=datetime.fromisoformat(event["commence_time"].replace("Z", "+00:00")),
            venue=None,
        )

    def _to_odds_snapshot(self, event: dict, fixture_id: str) -> OddsSnapshot | None:
        h2h = self._best_h2h(event)
        if h2h is None:
            logger.warning("No h2h market found for event %r", event.get("id"))
            return None

        home_team = event["home_team"]
        away_team = event["away_team"]
        home_win = h2h.get(home_team, 0.0)
        away_win = h2h.get(away_team, 0.0)
        draw = h2h.get("Draw", 0.0)

        return OddsSnapshot(
            fixture_id=fixture_id,
            market="double_chance",
            bookmaker=h2h["_bookmaker"],
            home_draw=self._dc_odds(home_win, draw),
            home_away=self._dc_odds(home_win, away_win),
            draw_away=self._dc_odds(draw, away_win),
            fetched_at=datetime.now(tz=timezone.utc),
        )

    def _best_h2h(self, event: dict) -> dict | None:
        bookmakers: list[dict] = event.get("bookmakers", [])
        if not bookmakers:
            return None

        bookmaker_map: dict[str, dict] = {b["key"]: b for b in bookmakers}

        selected: dict | None = None
        for preferred in PREFERRED_BOOKMAKERS:
            if preferred in bookmaker_map:
                selected = bookmaker_map[preferred]
                break

        if selected is None:
            selected = bookmakers[0]

        for market in selected.get("markets", []):
            if market["key"] == "h2h":
                parsed: dict = {"_bookmaker": selected["key"]}
                for outcome in market.get("outcomes", []):
                    parsed[outcome["name"]] = outcome["price"]
                return parsed

        return None

    @staticmethod
    def _dc_odds(p1: float, p2: float) -> float:
        """
        Derive double chance odds from two 1X2 decimal prices.
        Adds implied probabilities, converts back to decimal odds.
        Returns 0.0 if either input is non-positive.
        """
        if p1 <= 0 or p2 <= 0:
            return 0.0
        return round(1.0 / (1.0 / p1 + 1.0 / p2), 4)
