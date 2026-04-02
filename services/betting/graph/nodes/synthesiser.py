from dataclasses import asdict
from datetime import datetime, timezone

from betting.graph.state import BettingState
from betting.models.signal import Signal
from betting.models.verdict import Verdict


class SynthesiserNode:
    def __init__(
        self,
        weights: dict[str, float],
        confidence_threshold: float,
    ) -> None:
        self._weights = weights
        self._confidence_threshold = confidence_threshold

    def __call__(self, state: BettingState) -> dict:
        signals_raw = [
            state.get("statistical_signal"),
            state.get("market_signal"),
        ]
        signals = [Signal(**s) for s in signals_raw if s is not None]

        # Derive the active market from the odds snapshot being processed,
        # falling back to the first entry in the markets list.
        market = (
            state.get("odds_snapshot", {}).get("market")
            or (state.get("markets") or ["unknown"])[0]
        )

        # 1. Veto check
        for signal in signals:
            if signal.veto:
                verdict = Verdict(
                    fixture_id=state["fixture"]["id"],
                    market=market,
                    recommendation="skip",
                    consensus_confidence=0.0,
                    expected_value=0.0,
                    signals_used=len(signals),
                    synthesised_at=datetime.now(tz=timezone.utc),
                    skip_reason=signal.veto_reason or "veto",
                )
                return {"verdict": asdict(verdict)}

        # 2. No signals available
        if not signals:
            verdict = Verdict(
                fixture_id=state["fixture"]["id"],
                market=market,
                recommendation="skip",
                consensus_confidence=0.0,
                expected_value=0.0,
                signals_used=0,
                synthesised_at=datetime.now(tz=timezone.utc),
                skip_reason="no signals available",
            )
            return {"verdict": asdict(verdict)}

        # 3. Weighted vote
        total_weight = sum(
            self._weights.get(s.agent_id, 0.0) for s in signals
        )
        if total_weight == 0:
            # No weights configured for any active agent — treat as unweightable
            verdict = Verdict(
                fixture_id=state["fixture"]["id"],
                market=market,
                recommendation="skip",
                consensus_confidence=0.0,
                expected_value=0.0,
                signals_used=len(signals),
                synthesised_at=datetime.now(tz=timezone.utc),
                skip_reason="no agent weights configured",
            )
            return {"verdict": asdict(verdict)}

        weighted_confidence = sum(
            s.confidence * self._weights.get(s.agent_id, 0.0)
            for s in signals
        ) / total_weight

        weighted_edge = sum(
            s.edge * self._weights.get(s.agent_id, 0.0)
            for s in signals
        ) / total_weight

        # 4. Selection — use statistical agent's selection as primary
        #    fall back to first available signal's selection
        selection = ""
        stat_signal = next((s for s in signals if s.agent_id == "statistical"), None)
        if stat_signal:
            selection = stat_signal.selection
        elif signals:
            selection = signals[0].selection

        # 5. Threshold gate
        recommendation = (
            "back"
            if weighted_confidence >= self._confidence_threshold and weighted_edge > 0
            else "skip"
        )

        skip_reason = None
        if recommendation == "skip":
            if weighted_edge <= 0:
                skip_reason = f"no edge (weighted_edge={weighted_edge:.4f})"
            else:
                skip_reason = (
                    f"confidence below threshold "
                    f"({weighted_confidence:.3f} < {self._confidence_threshold})"
                )

        verdict = Verdict(
            fixture_id=state["fixture"]["id"],
            market=market,
            recommendation=recommendation,  # type: ignore[arg-type]
            consensus_confidence=weighted_confidence,
            expected_value=weighted_edge,
            signals_used=len(signals),
            synthesised_at=datetime.now(tz=timezone.utc),
            selection=selection,
            skip_reason=skip_reason,
        )
        return {"verdict": asdict(verdict)}
