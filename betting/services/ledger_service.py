from __future__ import annotations

from typing import TYPE_CHECKING

from betting.interfaces.ledger_repository import ILedgerRepository

if TYPE_CHECKING:
    from betting.graph.state import BettingState


class LedgerService:
    def __init__(self, repository: ILedgerRepository) -> None:
        self._repository = repository

    def record(self, state: BettingState) -> None:
        self._repository.record(state)
