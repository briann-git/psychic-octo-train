import logging
from datetime import datetime, timezone

import httpx

from betting.config.league_config import LeagueConfigLoader
from betting.config.market_config import MarketConfigLoader, MarketDefinition
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
        market_loader: MarketConfigLoader | None = None,
    ) -> None:
        self._api_key = api_key
        self._league_loader = league_loader or LeagueConfigLoader()
        self._market_loader = market_loader or MarketConfigLoader()
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

    def fetch_odds(
        self, fixture: Fixture, markets: list[str]
    ) -> OddsSnapshot | None:
        sport_key = self._league_loader.odds_api_key(fixture.league)
        if sport_key is None:
            logger.warning("League %r not in config — cannot fetch odds", fixture.league)
            return None
        events = self._fetch_events(sport_key)
        event = next((e for e in events if e["id"] == fixture.id), None)
        if not event:
            return None

        for market_id in markets:
            snapshot = self._build_odds_snapshot(event, fixture.id, market_id)
            if snapshot:
                return snapshot
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_events(self, sport_key: str) -> list[dict]:
        if sport_key in self._cache:
            logger.info("Cache hit for sport key %r", sport_key)
            return self._cache[sport_key]

        market_keys = list({
            m.odds_api_market_key
            for m in self._market_loader.active_markets()
        })

        logger.info("Fetching events for sport key %r, markets %s", sport_key, market_keys)
        try:
            response = httpx.get(
                f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds",
                params={
                    "apiKey": self._api_key,
                    "regions": "eu",
                    "markets": ",".join(market_keys),
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

    def _build_odds_snapshot(
        self, event: dict, fixture_id: str, market_id: str
    ) -> OddsSnapshot | None:
        market = self._market_loader.get(market_id)
        if not market:
            logger.warning("Market %r not in registry", market_id)
            return None

        if market.odds_derivation == "implied_sum":
            return self._build_implied_sum_snapshot(event, fixture_id, market)
        else:
            return self._build_direct_snapshot(event, fixture_id, market)

    def _build_implied_sum_snapshot(
        self, event: dict, fixture_id: str, market: MarketDefinition
    ) -> OddsSnapshot | None:
        source_prices = self._extract_source_prices(event, market.odds_api_market_key)
        if not source_prices:
            return None

        ftr_prices = self._map_to_ftr_prices(event, source_prices)

        selection_odds: dict[str, float] = {}
        for sel in market.selections:
            # Derived markets must use string wins_if (pipe-separated FTR codes)
            if not isinstance(sel.wins_if, str):
                logger.warning(
                    "Derived market %r selection %r has non-string wins_if — skipping",
                    market.id, sel.id,
                )
                return None
            codes = [c.strip() for c in sel.wins_if.split("|")]
            component_odds = [
                ftr_prices[code]
                for code in codes
                if code in ftr_prices
            ]
            if len(component_odds) != len(codes):
                logger.warning(
                    "Missing component odds for selection %r in market %r",
                    sel.id, market.id,
                )
                return None
            selection_odds[sel.id] = self._combine_implied(component_odds)

        bookmaker = source_prices.get("_bookmaker", "unknown")
        return self._to_odds_snapshot(fixture_id, market.id, selection_odds, bookmaker)

    def _build_direct_snapshot(
        self, event: dict, fixture_id: str, market: MarketDefinition
    ) -> OddsSnapshot | None:
        source_prices = self._extract_source_prices(event, market.odds_api_market_key)
        if not source_prices:
            return None

        selection_odds: dict[str, float] = {}
        for sel in market.selections:
            price = source_prices.get(sel.label, 0.0)
            selection_odds[sel.id] = price

        bookmaker = source_prices.get("_bookmaker", "unknown")
        return self._to_odds_snapshot(fixture_id, market.id, selection_odds, bookmaker)

    def _extract_source_prices(self, event: dict, market_key: str) -> dict | None:
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
            if market["key"] == market_key:
                parsed: dict = {"_bookmaker": selected["key"]}
                for outcome in market.get("outcomes", []):
                    parsed[outcome["name"]] = outcome["price"]
                return parsed

        return None

    def _map_to_ftr_prices(self, event: dict, source_prices: dict) -> dict[str, float]:
        return {
            "H": source_prices.get(event["home_team"], 0.0),
            "D": source_prices.get("Draw", 0.0),
            "A": source_prices.get(event["away_team"], 0.0),
        }

    def _to_odds_snapshot(
        self,
        fixture_id: str,
        market_id: str,
        selection_odds: dict[str, float],
        bookmaker: str,
    ) -> OddsSnapshot:
        return OddsSnapshot(
            fixture_id=fixture_id,
            market=market_id,
            bookmaker=bookmaker,
            selections=selection_odds,
            fetched_at=datetime.now(tz=timezone.utc),
        )

    def fetch_results(
        self,
        league: str,
        days_from: int = 1,
    ) -> list[dict]:
        """
        GET /v4/sports/{sport_key}/scores?daysFrom={days_from}
        Returns completed matches only (completed=true).
        """
        sport_key = self._league_loader.odds_api_key(league)
        if not sport_key:
            logger.warning("League %r not in league config — cannot fetch results", league)
            return []

        try:
            response = httpx.get(
                f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores",
                params={
                    "apiKey": self._api_key,
                    "daysFrom": days_from,
                },
                timeout=10,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "HTTP error fetching results for %s — status %s",
                league, exc.response.status_code,
            )
            raise

        return [e for e in response.json() if e.get("completed")]

    @staticmethod
    def _combine_implied(odds_list: list[float]) -> float:
        """
        Combines N decimal odds by adding implied probabilities.
        Returns 0.0 if any input is non-positive.
        """
        if any(o <= 0 for o in odds_list):
            return 0.0
        return round(1.0 / sum(1.0 / o for o in odds_list), 4)
