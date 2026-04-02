"""P&L summary service — computes profit and loss across all settled picks."""

import logging
from dataclasses import dataclass, field

from betting.interfaces.ledger_repository import ILedgerRepository

logger = logging.getLogger(__name__)

CALIBRATION_BUCKETS = [
    (0.60, 0.65),
    (0.65, 0.70),
    (0.70, 0.75),
    (0.75, 1.01),
]


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
    total_skips: int = 0
    skip_reasons: dict[str, int] = field(default_factory=dict)
    clv_average: float | None = None
    calibration_buckets: list[dict] = field(default_factory=list)


class PnlService:
    def __init__(self, ledger_repo: ILedgerRepository) -> None:
        self._ledger = ledger_repo

    def compute(self, profile_id: str | None = None) -> PnlSummary:
        """Computes P&L across all settled picks, optionally scoped by profile."""
        picks = self._ledger.get_all_picks(profile_id=profile_id)
        skips = self._ledger.get_all_skips(profile_id=profile_id)

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

        # Skip reason aggregation
        skip_reasons: dict[str, int] = {}
        for skip in skips:
            reason = skip.get("skip_reason") or "unknown"
            # Normalise verbose reasons to categories
            if "confidence below threshold" in reason:
                key = "confidence_below_threshold"
            elif "no edge" in reason:
                key = "no_edge"
            elif "no signals" in reason:
                key = "no_signals_available"
            elif "veto" in reason:
                key = "veto"
            elif "ineligible" in reason:
                key = "ineligible_fixture"
            else:
                key = reason
            skip_reasons[key] = skip_reasons.get(key, 0) + 1

        # CLV calculation
        clv_values = []
        for pick in picks:
            selection_odds = pick.get("selection_odds") or pick.get("odds", 0)
            opening_odds = pick.get("opening_odds")
            if opening_odds and opening_odds > 0 and selection_odds > 0:
                # CLV = implied prob at opening - implied prob at analysis
                # Positive = opening implied prob higher (opening odds shorter)
                # Negative = opening implied prob lower (you got shorter odds than opening)
                clv = (1.0 / opening_odds) - (1.0 / selection_odds)
                clv_values.append(clv)

        clv_average = sum(clv_values) / len(clv_values) if clv_values else None

        # Confidence calibration buckets
        buckets = []
        settled_picks = [p for p in picks if p.get("outcome") in ("won", "lost")]

        for low, high in CALIBRATION_BUCKETS:
            bucket_picks = [
                p for p in settled_picks
                if low <= (p.get("confidence") or 0.0) < high
            ]
            won_count = sum(1 for p in bucket_picks if p.get("outcome") == "won")
            buckets.append({
                "range": f"{low:.2f}-{high:.2f}".replace("-1.01", "+"),
                "picks": len(bucket_picks),
                "won": won_count,
                "win_rate": won_count / len(bucket_picks) if bucket_picks else None,
            })

        calibration_buckets = [b for b in buckets if b["picks"] > 0]

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
            total_skips=len(skips),
            skip_reasons=skip_reasons,
            clv_average=clv_average,
            calibration_buckets=calibration_buckets,
        )
