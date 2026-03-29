from dataclasses import asdict
from datetime import datetime, timezone

from betting.graph.state import BettingState
from betting.models.signal import Signal
from betting.models.verdict import Verdict


class SynthesiserNode:
    """
    STUB — spine only.
    When real agents are wired in, this node:
      1. Checks each signal for veto flag
      2. Applies weighted vote across available signals
      3. Compares weighted confidence to CONFIDENCE_THRESHOLD
      4. Returns Verdict with recommendation
    """

    def __call__(self, state: BettingState) -> dict:
        statistical = state.get("statistical_signal")

        if not statistical:
            verdict = Verdict(
                fixture_id=state["fixture"]["id"],
                market=state["markets"][0],
                recommendation="skip",
                consensus_confidence=0.0,
                expected_value=0.0,
                signals_used=0,
                synthesised_at=datetime.now(tz=timezone.utc),
                skip_reason="no signals available",
            )
        else:
            signal = Signal(**statistical)
            verdict = Verdict(
                fixture_id=signal.fixture_id,
                market=state["markets"][0],
                recommendation=signal.recommendation,
                consensus_confidence=signal.confidence,
                expected_value=signal.edge,
                signals_used=1,
                synthesised_at=datetime.now(tz=timezone.utc),
                selection=signal.selection,
            )

        return {"verdict": asdict(verdict)}
