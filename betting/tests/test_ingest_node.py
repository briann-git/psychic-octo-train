"""Tests for IngestNode."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from betting.graph.nodes.ingest import IngestNode
from betting.graph.state import BettingState
from betting.services.fixture_service import FixtureService


def _fixture_dict() -> dict:
    return {
        "id": "fix-001",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "league": "PL",
        "season": "2024/25",
        "matchday": 30,
        "kickoff": datetime(2025, 4, 1, 15, 0, tzinfo=timezone.utc),
        "venue": "Emirates Stadium",
    }


def _odds_dict() -> dict:
    return {
        "fixture_id": "fix-001",
        "market": "double_chance",
        "bookmaker": "stub",
        "home_draw": 1.40,
        "home_away": 1.25,
        "draw_away": 2.10,
        "fetched_at": datetime.now(tz=timezone.utc),
    }


def _make_state(**overrides) -> BettingState:
    base: BettingState = {
        "fixture": _fixture_dict(),
        "markets": ["double_chance"],
        "odds_snapshot": _odds_dict(),
        "eligible": True,
        "statistical_signal": None,
        "verdict": None,
        "recorded": False,
        "errors": [],
    }
    base.update(overrides)
    return base


def _make_node() -> IngestNode:
    return IngestNode(fixture_service=MagicMock(spec=FixtureService))


class TestIngestNode:
    def test_valid_state_returns_eligible_true(self):
        node = _make_node()
        result = node(_make_state())
        assert result["eligible"] is True
        assert result["errors"] == []

    def test_missing_fixture_sets_ineligible(self):
        node = _make_node()
        state = _make_state(fixture={})
        result = node(state)
        assert result["eligible"] is False
        assert any("fixture" in e for e in result["errors"])

    def test_missing_odds_sets_ineligible(self):
        node = _make_node()
        state = _make_state(odds_snapshot={})
        result = node(state)
        assert result["eligible"] is False
        assert any("odds_snapshot" in e for e in result["errors"])

    def test_pre_marked_ineligible_preserved(self):
        node = _make_node()
        state = _make_state(eligible=False)
        result = node(state)
        assert result["eligible"] is False
        assert any("ineligible" in e for e in result["errors"])

    def test_existing_errors_are_preserved(self):
        node = _make_node()
        state = _make_state(errors=["earlier: something bad"], eligible=False)
        result = node(state)
        assert "earlier: something bad" in result["errors"]
