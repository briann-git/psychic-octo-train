"""Tests for LedgerNode stale signal warning."""

import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from betting.graph.nodes.ledger import STALE_SIGNAL_HOURS, LedgerNode
from betting.services.ledger_service import LedgerService


def _make_node(profile_id: str = "default-paper", profile_type: str = "paper") -> LedgerNode:
    service = MagicMock(spec=LedgerService)
    return LedgerNode(ledger_service=service, profile_id=profile_id, profile_type=profile_type)


def _base_state(
    statistical_signal: dict | None = None,
    market_signal: dict | None = None,
) -> dict:
    return {
        "fixture": {
            "id": "fix_1",
            "home_team": "Team A",
            "away_team": "Team B",
        },
        "markets": ["double_chance"],
        "odds_snapshot": {},
        "eligible": True,
        "statistical_signal": statistical_signal,
        "market_signal": market_signal,
        "verdict": {
            "fixture_id": "fix_1",
            "market": "double_chance",
            "recommendation": "skip",
            "consensus_confidence": 0.5,
            "expected_value": 0.0,
            "signals_used": 0,
            "synthesised_at": datetime.now(tz=timezone.utc).isoformat(),
            "skip_reason": "test",
        },
        "recorded": False,
        "errors": [],
    }


class TestStaleSignalWarning:
    def test_stale_signal_logs_warning(self, caplog):
        stale_ts = (
            datetime.now(tz=timezone.utc) - timedelta(hours=STALE_SIGNAL_HOURS + 1)
        ).isoformat()
        signal = {"data_timestamp": stale_ts}

        node = _make_node()
        state = _base_state(statistical_signal=signal)

        with caplog.at_level(logging.WARNING):
            node(state)

        assert any("Stale signal" in record.message for record in caplog.records)
        assert any("statistical_signal" in record.message for record in caplog.records)

    def test_fresh_signal_does_not_log_warning(self, caplog):
        fresh_ts = (
            datetime.now(tz=timezone.utc) - timedelta(hours=1)
        ).isoformat()
        signal = {"data_timestamp": fresh_ts}

        node = _make_node()
        state = _base_state(statistical_signal=signal)

        with caplog.at_level(logging.WARNING):
            node(state)

        stale_messages = [
            r for r in caplog.records if "Stale signal" in r.message
        ]
        assert len(stale_messages) == 0

    def test_missing_data_timestamp_handled_gracefully(self, caplog):
        signal = {"agent_id": "statistical"}  # no data_timestamp

        node = _make_node()
        state = _base_state(statistical_signal=signal)

        with caplog.at_level(logging.WARNING):
            node(state)

        stale_messages = [
            r for r in caplog.records if "Stale signal" in r.message
        ]
        assert len(stale_messages) == 0

    def test_market_signal_stale_warning(self, caplog):
        stale_ts = (
            datetime.now(tz=timezone.utc) - timedelta(hours=STALE_SIGNAL_HOURS + 2)
        ).isoformat()
        signal = {"data_timestamp": stale_ts}

        node = _make_node()
        state = _base_state(market_signal=signal)

        with caplog.at_level(logging.WARNING):
            node(state)

        assert any("market_signal" in record.message for record in caplog.records)

    def test_no_signals_no_warning(self, caplog):
        node = _make_node()
        state = _base_state()

        with caplog.at_level(logging.WARNING):
            node(state)

        stale_messages = [
            r for r in caplog.records if "Stale signal" in r.message
        ]
        assert len(stale_messages) == 0
