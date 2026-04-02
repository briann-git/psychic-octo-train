from betting.graph.state import BettingState
from betting.services.fixture_service import FixtureService


class IngestNode:
    """
    Validates that the pre-populated fixture and odds_snapshot are present
    and the fixture is marked eligible.  Does not fetch data — the graph
    runner (scheduler.py) pre-populates the state before invocation.
    """

    def __init__(self, fixture_service: FixtureService) -> None:
        self._fixture_service = fixture_service

    def __call__(self, state: BettingState) -> dict:
        errors: list[str] = list(state.get("errors", []))

        if not state.get("fixture"):
            errors.append("ingest: fixture missing from state")
            return {"eligible": False, "errors": errors}

        if not state.get("odds_snapshot"):
            errors.append("ingest: odds_snapshot missing from state")
            return {"eligible": False, "errors": errors}

        if not state.get("eligible", False):
            errors.append("ingest: fixture marked ineligible by runner")
            return {"eligible": False, "errors": errors}

        return {"eligible": True, "errors": errors}
