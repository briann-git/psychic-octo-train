from abc import ABC, abstractmethod
from datetime import datetime
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

    @abstractmethod
    def get_all_skips(self) -> list[dict]:
        """Returns all rows from the skips table."""
        ...

    @abstractmethod
    def record_pick_signals(
        self,
        pick_id: str,
        signals: list[dict],
    ) -> None:
        """
        Persists agent signals for a given pick.
        Each dict in signals is a serialised Signal.
        Only called when recommendation == "back".
        """
        ...

    @abstractmethod
    def upsert_fixture_calendar(self, fixtures: list["Fixture"]) -> None:
        """
        Inserts or replaces fixtures in the calendar.
        Prunes fixtures whose kickoff has already passed.
        """
        ...

    @abstractmethod
    def get_calendar_fixtures(
        self,
        from_dt: datetime,
        to_dt: datetime,
        leagues: list[str] | None = None,
    ) -> list[dict]:
        """
        Returns fixtures from the calendar within the given kickoff window.
        Optionally filtered by league.
        """
        ...
