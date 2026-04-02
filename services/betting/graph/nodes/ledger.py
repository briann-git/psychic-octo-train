import logging
from dataclasses import asdict
from datetime import datetime, timezone

from betting.graph.state import BettingState
from betting.models.verdict import Verdict
from betting.services.ledger_service import LedgerService

logger = logging.getLogger(__name__)

STALE_SIGNAL_HOURS = 6


class LedgerNode:
    def __init__(
        self,
        ledger_service: LedgerService,
        profile_id: str = "default-paper",
        profile_type: str = "paper",
    ) -> None:
        self._service = ledger_service
        self._profile_id = profile_id
        self._profile_type = profile_type

    def __call__(self, state: BettingState) -> dict:
        # Ensure a verdict is present — if the pipeline short-circuited (e.g.
        # ineligible fixture bypassed the synthesiser), create a skip verdict here.
        working_state = dict(state)
        if not working_state.get("verdict"):
            errors = list(working_state.get("errors", []))
            skip_reason = errors[0] if errors else "ineligible fixture"
            market = (
                working_state.get("odds_snapshot", {}).get("market")
                or (working_state.get("markets") or ["double_chance"])[0]
            )
            stub_verdict = Verdict(
                fixture_id=working_state["fixture"]["id"],
                market=market,
                recommendation="skip",
                consensus_confidence=0.0,
                expected_value=0.0,
                signals_used=0,
                synthesised_at=datetime.now(tz=timezone.utc),
                skip_reason=skip_reason,
            )
            working_state["verdict"] = asdict(stub_verdict)

        try:
            self._service.record(working_state, profile_id=self._profile_id)  # type: ignore[arg-type]
            result = {"recorded": True, "verdict": working_state["verdict"]}

            if working_state.get("verdict") and self._profile_type == "paper":
                verdict = working_state["verdict"]
                if verdict.get("recommendation") == "back":
                    logger.info(
                        "[PAPER] Would back %s — %s vs %s, selection=%s, confidence=%.3f, edge=%.4f",
                        verdict["fixture_id"],
                        state["fixture"]["home_team"],
                        state["fixture"]["away_team"],
                        verdict.get("selection"),
                        verdict.get("consensus_confidence", 0),
                        verdict.get("expected_value", 0),
                    )

            # Check for stale signals
            signals_to_check = [
                ("statistical_signal", state.get("statistical_signal")),
                ("market_signal", state.get("market_signal")),
            ]

            for name, signal in signals_to_check:
                if not signal:
                    continue
                ts_raw = signal.get("data_timestamp")
                if not ts_raw:
                    continue
                try:
                    ts = datetime.fromisoformat(ts_raw)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    age_hours = (datetime.now(tz=timezone.utc) - ts).total_seconds() / 3600
                    if age_hours > STALE_SIGNAL_HOURS:
                        logger.warning(
                            "Stale signal from %s for fixture %s — %.1f hours old",
                            name, state["fixture"].get("id"), age_hours,
                        )
                except (ValueError, TypeError):
                    pass

            return result
        except Exception as exc:
            logger.warning(
                "LedgerNode error for fixture %s: %s",
                state["fixture"].get("id"),
                exc,
            )
            return {
                "recorded": False,
                "errors": list(state.get("errors", [])) + [f"ledger: {exc}"],
            }
