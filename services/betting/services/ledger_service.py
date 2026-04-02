from __future__ import annotations

from typing import TYPE_CHECKING

from betting.interfaces.ledger_repository import ILedgerRepository

if TYPE_CHECKING:
    from betting.graph.state import BettingState


class LedgerService:
    def __init__(self, repository: ILedgerRepository) -> None:
        self._repository = repository

    def record(self, state: BettingState, profile_id: str = "default-paper") -> None:
        self._repository.record(state, profile_id=profile_id)

        verdict = state.get("verdict", {})
        if verdict.get("recommendation") == "back":
            # Collect all available signals from state
            signals = [
                s for s in [
                    state.get("statistical_signal"),
                    state.get("market_signal"),
                ]
                if s is not None
            ]
            if signals:
                # Retrieve the pick id just written
                pick = self._repository.get_by_fixture(
                    state["fixture"]["id"], profile_id=profile_id
                )
                if pick and "id" in pick:
                    self._repository.record_pick_signals(pick["id"], signals)
