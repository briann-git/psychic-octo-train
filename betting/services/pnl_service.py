"""P&L summary service — computes profit and loss across all settled picks."""

import logging
from dataclasses import dataclass

from betting.interfaces.ledger_repository import ILedgerRepository

logger = logging.getLogger(__name__)


@dataclass
class PnlSummary:
    total_picks: int
    settled: int
    pending: int
    won: int
    lost: int
    void: int
    win_rate: float         # won / (won + lost), 0.0 if no settled non-void bets
    total_staked: float
    gross_return: float     # sum of (odds * stake) for won bets
    net_pnl: float          # gross_return - total_staked
    roi: float              # net_pnl / total_staked, 0.0 if no staked bets


class PnlService:
    def __init__(self, ledger_repo: ILedgerRepository) -> None:
        self._ledger = ledger_repo

    def compute(self) -> PnlSummary:
        """Computes P&L across all settled picks."""
        picks = self._ledger.get_all_picks()

        total_picks = len(picks)
        settled = 0
        pending = 0
        won = 0
        lost = 0
        void = 0
        total_staked = 0.0
        gross_return = 0.0

        for pick in picks:
            outcome = pick.get("outcome")
            if outcome is None:
                pending += 1
            else:
                settled += 1
                if outcome == "won":
                    won += 1
                    total_staked += pick.get("stake", 0.0)
                    odds_value = pick.get("selection_odds") or pick.get("odds", 0.0)
                    gross_return += odds_value * pick.get("stake", 0.0)
                elif outcome == "lost":
                    lost += 1
                    total_staked += pick.get("stake", 0.0)
                elif outcome == "void":
                    void += 1

        net_pnl = gross_return - total_staked
        win_denominator = won + lost
        win_rate = won / win_denominator if win_denominator > 0 else 0.0
        roi = net_pnl / total_staked if total_staked > 0 else 0.0

        return PnlSummary(
            total_picks=total_picks,
            settled=settled,
            pending=pending,
            won=won,
            lost=lost,
            void=void,
            win_rate=win_rate,
            total_staked=total_staked,
            gross_return=gross_return,
            net_pnl=net_pnl,
            roi=roi,
        )
