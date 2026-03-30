from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from betting.graph.state import BettingState
    from betting.models.fixture import Fixture
    from betting.models.odds import OddsSnapshot


class ILedgerRepository(ABC):
    @abstractmethod
    def record(self, state: "BettingState") -> None:
        ...

    @abstractmethod
    def get_by_fixture(self, fixture_id: str) -> dict | None:
        ...

    @abstractmethod
    def save_odds_snapshot(
        self,
        fixture: "Fixture",
        odds: "OddsSnapshot",
        snapshot_type: str,
    ) -> None:
        ...

    @abstractmethod
    def get_odds_history(self, fixture_id: str) -> list[dict]:
        """Returns all rows for fixture ordered by fetched_at ascending."""
        ...

    @abstractmethod
    def get_pending_picks(self) -> list[dict]:
        """Returns all picks where outcome IS NULL."""
        ...

    @abstractmethod
    def settle_pick(self, pick_id: str, outcome: str) -> None:
        """Sets outcome and settled_at for the given pick id."""
        ...

    @abstractmethod
    def get_all_picks(self) -> list[dict]:
        """Returns all picks regardless of outcome."""
        ...
