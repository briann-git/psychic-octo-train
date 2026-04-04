import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

import httpx

from betting.config.league_config import LeagueConfigLoader
from betting.config.market_config import MarketConfigLoader, MarketDefinition
from betting.interfaces.fixture_provider import IFixtureProvider
from betting.interfaces.odds_provider import IOddsProvider
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot
from betting.utils import season_from_date

logger = logging.getLogger(__name__)

_HEARTBEAT_DIR = os.environ.get("HEARTBEAT_DIR", "/data/heartbeat")
_QUOTA_FILE = os.path.join(_HEARTBEAT_DIR, "odds_quota.json")


def _persist_quota(response: httpx.Response) -> None:
    """Write x-requests-* headers from an Odds API response to a JSON file."""
    remaining = response.headers.get("x-requests-remaining")
    used = response.headers.get("x-requests-used")
    last = response.headers.get("x-requests-last")
    if remaining is None and used is None:
        return
    payload = {
        "remaining": int(remaining) if remaining is not None else None,
        "used": int(used) if used is not None else None,
        "last": int(last) if last is not None else None,
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    try:
        os.makedirs(_HEARTBEAT_DIR, exist_ok=True)
        tmp = _QUOTA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(tmp, _QUOTA_FILE)
    except OSError as exc:
        logger.warning("Could not write odds quota file: %s", exc)

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
        self._historical_cache: dict[str, list[dict]] = {}

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
            try:
                events = self._fetch_events(sport_key)
            except Exception:
                logger.warning("Failed to fetch events for league %r (sport_key=%r) — skipping", league, sport_key)
                continue
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

    def fetch_all_odds(
        self, fixture: Fixture, markets: list[str]
    ) -> list[OddsSnapshot]:
        """Return an OddsSnapshot for every market that has available odds.

        Overrides the default implementation to avoid repeated event lookups
        by resolving the event once and iterating markets against it.
        """
        sport_key = self._league_loader.odds_api_key(fixture.league)
        if sport_key is None:
            logger.warning("League %r not in config — cannot fetch odds", fixture.league)
            return []
        events = self._fetch_events(sport_key)
        event = next((e for e in events if e["id"] == fixture.id), None)
        if not event:
            return []

        snapshots: list[OddsSnapshot] = []
        for market_id in markets:
            snapshot = self._build_odds_snapshot(event, fixture.id, market_id)
            if snapshot:
                snapshots.append(snapshot)
        return snapshots

    # ------------------------------------------------------------------
    # Historical odds (backtesting)
    # ------------------------------------------------------------------

    def fetch_historical_odds_for_match(
        self,
        fixture: "Fixture",
        as_of: datetime,
        markets: list[str],
    ) -> list[OddsSnapshot]:
        """
        Fetch pre-match odds for a single fixture using The Odds API historical
        endpoint (GET /v4/historical/sports/{sport}/odds?date={as_of}).

        The response format mirrors the live /odds endpoint, so all existing
        snapshot-building helpers are reused directly.

        Results are cached per (sport_key, as_of date) to avoid redundant
        paid API calls within a single backtest run.
        """
        sport_key = self._league_loader.odds_api_key(fixture.league)
        if sport_key is None:
            logger.warning("League %r not in config — cannot fetch historical odds", fixture.league)
            return []

        cache_key = f"{sport_key}_{as_of.date().isoformat()}"
        if cache_key not in self._historical_cache:
            market_keys = list({
                m.odds_api_market_key
                for m in self._market_loader.active_markets()
            })
            try:
                response = httpx.get(
                    f"https://api.the-odds-api.com/v4/historical/sports/{sport_key}/odds",
                    params={
                        "apiKey": self._api_key,
                        "regions": "eu",
                        "markets": ",".join(market_keys),
                        "oddsFormat": "decimal",
                        "date": as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    },
                    timeout=15,
                )
                response.raise_for_status()
                payload = response.json()
                # Historical endpoint wraps data in {"data": [...], "timestamp": ..., ...}
                events = payload.get("data", payload) if isinstance(payload, dict) else payload
                self._historical_cache[cache_key] = events if isinstance(events, list) else []
            except httpx.HTTPStatusError as exc:
                safe_url = str(exc.request.url).split("apiKey")[0] + "apiKey=REDACTED"
                logger.error(
                    "HTTP error from Odds API historical endpoint — status %s, url %s",
                    exc.response.status_code,
                    safe_url,
                )
                return []
            except Exception as exc:
                logger.error("Failed to fetch historical odds for %s on %s: %s", fixture.league, as_of.date(), exc)
                return []

        events = self._historical_cache[cache_key]

        # Match event by team names (Odds API names, already on the Fixture)
        event = next(
            (
                e for e in events
                if e.get("home_team") == fixture.home_team
                and e.get("away_team") == fixture.away_team
            ),
            None,
        )
        if event is None:
            logger.debug(
                "No historical odds event found for %s vs %s on %s",
                fixture.home_team, fixture.away_team, as_of.date(),
            )
            return []

        snapshots: list[OddsSnapshot] = []
        for market_id in markets:
            snapshot = self._build_odds_snapshot(event, fixture.id, market_id)
            if snapshot:
                snapshots.append(snapshot)
        return snapshots

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
            safe_url = str(exc.request.url).split("apiKey")[0] + "apiKey=REDACTED"
            logger.error(
                "HTTP error from Odds API — status %s, url %s",
                exc.response.status_code,
                safe_url,
            )
            raise

        _persist_quota(response)
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
            price = self._resolve_direct_price(source_prices, sel.label, sel.outcome_name, sel.outcome_point)
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
                parsed: dict[str, Any] = {
                    "_bookmaker": selected["key"],
                    "_outcomes": [],
                }
                for outcome in market.get("outcomes", []):
                    name = outcome.get("name")
                    price = outcome.get("price")
                    if not name or price is None:
                        continue
                    parsed["_outcomes"].append(
                        {
                            "name": name,
                            "price": float(price),
                            "point": outcome.get("point"),
                        }
                    )
                    # Backward-compatible fallback for direct label matching
                    if name not in parsed:
                        parsed[name] = float(price)
                return parsed

        return None

    def _map_to_ftr_prices(self, event: dict, source_prices: dict) -> dict[str, float]:
        return {
            "H": source_prices.get(event["home_team"], 0.0),
            "D": source_prices.get("Draw", 0.0),
            "A": source_prices.get(event["away_team"], 0.0),
        }

    @staticmethod
    def _resolve_direct_price(
        source_prices: dict,
        label: str,
        outcome_name: str | None,
        outcome_point: float | None,
    ) -> float:
        outcomes = source_prices.get("_outcomes", [])

        if outcome_name:
            for outcome in outcomes:
                name = outcome.get("name")
                price = outcome.get("price")
                point = outcome.get("point")
                if price is None:
                    continue
                if name != outcome_name:
                    continue
                if outcome_point is None:
                    return float(price)
                if point is None:
                    continue
                try:
                    if float(point) == float(outcome_point):
                        return float(price)
                except (TypeError, ValueError):
                    continue

            # Secondary fallback when only a name is provided
            if outcome_point is None:
                fallback = source_prices.get(outcome_name, 0.0)
                return float(fallback) if fallback else 0.0

        # Legacy behavior (label-based)
        fallback = source_prices.get(label, 0.0)
        return float(fallback) if fallback else 0.0

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
