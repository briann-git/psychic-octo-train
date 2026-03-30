import logging
from dataclasses import asdict
from datetime import datetime, timezone

from betting.graph.state import BettingState
from betting.models.verdict import Verdict
from betting.services.ledger_service import LedgerService

logger = logging.getLogger(__name__)


class LedgerNode:
    def __init__(
        self,
        ledger_service: LedgerService,
        paper_trading: bool = True,
    ) -> None:
        self._service = ledger_service
        self._paper_trading = paper_trading

    def __call__(self, state: BettingState) -> dict:
        # Ensure a verdict is present — if the pipeline short-circuited (e.g.
        # ineligible fixture bypassed the synthesiser), create a skip verdict here.
        working_state = dict(state)
        if not working_state.get("verdict"):
            errors = list(working_state.get("errors", []))
            skip_reason = errors[0] if errors else "ineligible fixture"
            stub_verdict = Verdict(
                fixture_id=working_state["fixture"]["id"],
                market=(working_state.get("markets") or ["double_chance"])[0],
                recommendation="skip",
                consensus_confidence=0.0,
                expected_value=0.0,
                signals_used=0,
                synthesised_at=datetime.now(tz=timezone.utc),
                skip_reason=skip_reason,
            )
            working_state["verdict"] = asdict(stub_verdict)

        try:
            self._service.record(working_state)  # type: ignore[arg-type]
            result = {"recorded": True, "verdict": working_state["verdict"]}

            if working_state.get("verdict") and self._paper_trading:
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
