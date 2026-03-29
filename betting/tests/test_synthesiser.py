"""Tests for the real SynthesiserNode weighted vote."""

from dataclasses import asdict
from datetime import datetime, timezone

import pytest

from betting.graph.nodes.synthesiser import SynthesiserNode
from betting.graph.state import BettingState
from betting.models.signal import Signal


def _make_signal(
    agent_id: str = "statistical",
    recommendation: str = "back",
    confidence: float = 0.70,
    edge: float = 0.10,
    selection: str = "1X",
    veto: bool = False,
    veto_reason: str | None = None,
) -> dict:
    return asdict(Signal(
        agent_id=agent_id,
        fixture_id="fix-syn-001",
        recommendation=recommendation,  # type: ignore
        confidence=confidence,
        edge=edge,
        reasoning="test reasoning",
        data_timestamp=datetime.now(tz=timezone.utc),
        selection=selection,
        veto=veto,
        veto_reason=veto_reason,
    ))


def _make_state(
    statistical_signal=None,
    market_signal=None,
) -> BettingState:
    return {
        "fixture": {"id": "fix-syn-001"},
        "markets": ["double_chance"],
        "odds_snapshot": {},
        "eligible": True,
        "statistical_signal": statistical_signal,
        "market_signal": market_signal,
        "verdict": None,
        "recorded": False,
        "errors": [],
    }


def _make_synthesiser(weights=None, threshold=0.60) -> SynthesiserNode:
    if weights is None:
        weights = {"statistical": 0.60, "market": 0.40}
    return SynthesiserNode(weights=weights, confidence_threshold=threshold)


class TestVetoCheck:
    def test_veto_signal_causes_skip_regardless(self):
        synth = _make_synthesiser()
        state = _make_state(
            statistical_signal=_make_signal(
                confidence=0.90, edge=0.20, veto=True, veto_reason="data quality"
            ),
            market_signal=_make_signal(agent_id="market", confidence=0.80, edge=0.15),
        )
        result = synth(state)
        verdict = result["verdict"]
        assert verdict["recommendation"] == "skip"
        assert verdict["skip_reason"] == "data quality"

    def test_veto_in_market_signal_causes_skip(self):
        synth = _make_synthesiser()
        state = _make_state(
            statistical_signal=_make_signal(confidence=0.90, edge=0.20),
            market_signal=_make_signal(agent_id="market", veto=True, veto_reason="market error"),
        )
        result = synth(state)
        verdict = result["verdict"]
        assert verdict["recommendation"] == "skip"
        assert verdict["skip_reason"] == "market error"

    def test_veto_without_reason_uses_default(self):
        synth = _make_synthesiser()
        state = _make_state(
            statistical_signal=_make_signal(veto=True, veto_reason=None),
        )
        result = synth(state)
        assert result["verdict"]["skip_reason"] == "veto"


class TestNoSignals:
    def test_skip_when_no_signals(self):
        synth = _make_synthesiser()
        state = _make_state(statistical_signal=None, market_signal=None)
        result = synth(state)
        verdict = result["verdict"]
        assert verdict["recommendation"] == "skip"
        assert verdict["skip_reason"] == "no signals available"
        assert verdict["signals_used"] == 0


class TestWeightedVote:
    def test_weighted_confidence_computed_correctly(self):
        synth = _make_synthesiser(weights={"statistical": 0.60, "market": 0.40})
        state = _make_state(
            statistical_signal=_make_signal(agent_id="statistical", confidence=0.80, edge=0.10),
            market_signal=_make_signal(agent_id="market", confidence=0.60, edge=0.08),
        )
        result = synth(state)
        verdict = result["verdict"]
        # weighted_confidence = (0.80*0.60 + 0.60*0.40) / (0.60 + 0.40) = (0.48 + 0.24) / 1.0 = 0.72
        assert verdict["consensus_confidence"] == pytest.approx(0.72)

    def test_weighted_edge_computed_correctly(self):
        synth = _make_synthesiser(weights={"statistical": 0.60, "market": 0.40})
        state = _make_state(
            statistical_signal=_make_signal(agent_id="statistical", confidence=0.80, edge=0.10),
            market_signal=_make_signal(agent_id="market", confidence=0.60, edge=0.05),
        )
        result = synth(state)
        verdict = result["verdict"]
        # weighted_edge = (0.10*0.60 + 0.05*0.40) / 1.0 = 0.06 + 0.02 = 0.08
        assert verdict["expected_value"] == pytest.approx(0.08)

    def test_signals_used_count(self):
        synth = _make_synthesiser()
        state = _make_state(
            statistical_signal=_make_signal(confidence=0.80, edge=0.10),
            market_signal=_make_signal(agent_id="market", confidence=0.70, edge=0.08),
        )
        result = synth(state)
        assert result["verdict"]["signals_used"] == 2

    def test_only_statistical_signal_used_when_market_absent(self):
        synth = _make_synthesiser(weights={"statistical": 0.60, "market": 0.40})
        state = _make_state(
            statistical_signal=_make_signal(agent_id="statistical", confidence=0.75, edge=0.12),
            market_signal=None,
        )
        result = synth(state)
        verdict = result["verdict"]
        # Only statistical: total_weight=0.60, weighted_confidence = 0.75*0.60/0.60 = 0.75
        assert verdict["consensus_confidence"] == pytest.approx(0.75)
        assert verdict["signals_used"] == 1


class TestSelection:
    def test_statistical_selection_used_as_primary(self):
        synth = _make_synthesiser()
        state = _make_state(
            statistical_signal=_make_signal(agent_id="statistical", selection="1X", confidence=0.75, edge=0.10),
            market_signal=_make_signal(agent_id="market", selection="12", confidence=0.65, edge=0.08),
        )
        result = synth(state)
        assert result["verdict"]["selection"] == "1X"

    def test_first_signal_selection_used_when_no_statistical(self):
        synth = _make_synthesiser(weights={"market": 1.0})
        state = _make_state(
            statistical_signal=None,
            market_signal=_make_signal(agent_id="market", selection="X2", confidence=0.70, edge=0.10),
        )
        result = synth(state)
        assert result["verdict"]["selection"] == "X2"


class TestThresholdGate:
    def test_back_when_confidence_meets_threshold_and_positive_edge(self):
        synth = _make_synthesiser(threshold=0.60)
        state = _make_state(
            statistical_signal=_make_signal(confidence=0.70, edge=0.10),
        )
        result = synth(state)
        assert result["verdict"]["recommendation"] == "back"

    def test_skip_when_confidence_below_threshold(self):
        synth = _make_synthesiser(threshold=0.60)
        state = _make_state(
            statistical_signal=_make_signal(confidence=0.50, edge=0.10),
        )
        result = synth(state)
        verdict = result["verdict"]
        assert verdict["recommendation"] == "skip"
        assert "confidence below threshold" in verdict["skip_reason"]

    def test_skip_when_negative_edge_despite_high_confidence(self):
        synth = _make_synthesiser(threshold=0.60)
        state = _make_state(
            statistical_signal=_make_signal(confidence=0.90, edge=-0.05),
        )
        result = synth(state)
        verdict = result["verdict"]
        assert verdict["recommendation"] == "skip"
        assert "no edge" in verdict["skip_reason"]

    def test_skip_when_zero_edge(self):
        synth = _make_synthesiser(threshold=0.60)
        state = _make_state(
            statistical_signal=_make_signal(confidence=0.90, edge=0.0),
        )
        result = synth(state)
        assert result["verdict"]["recommendation"] == "skip"
