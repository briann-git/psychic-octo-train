from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from betting.graph.state import BettingState


class ILedgerRepository(ABC):
    @abstractmethod
    def record(self, state: "BettingState") -> None:
        ...

    @abstractmethod
    def get_by_fixture(self, fixture_id: str) -> dict | None:
        ...
