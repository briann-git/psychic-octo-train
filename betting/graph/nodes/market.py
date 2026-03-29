import logging
from dataclasses import asdict

from betting.graph.state import BettingState
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot
from betting.services.market_service import MarketService

logger = logging.getLogger(__name__)


class MarketNode:
    def __init__(self, market_service: MarketService) -> None:
        self._service = market_service

    def __call__(self, state: BettingState) -> dict:
        if not state.get("eligible"):
            return {}

        fixture = Fixture.from_dict(state["fixture"])
        odds = OddsSnapshot.from_dict(state["odds_snapshot"])

        try:
            signal = self._service.analyse(fixture, odds)
            return {"market_signal": asdict(signal)}
        except Exception as exc:
            logger.warning(
                "MarketNode error for fixture %s: %s",
                state["fixture"].get("id"), exc,
            )
            return {
                "errors": list(state.get("errors", [])) + [f"market: {exc}"]
            }
