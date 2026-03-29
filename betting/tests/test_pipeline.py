"""End-to-end pipeline integration tests using stub adapters and an in-memory SQLite DB."""

import os
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from betting.adapters.sqlite_ledger import SqliteLedgerRepository
from betting.graph.nodes.ingest import IngestNode
from betting.graph.nodes.ledger import LedgerNode
from betting.graph.nodes.statistical import StatisticalNode
from betting.graph.nodes.synthesiser import SynthesiserNode
from betting.graph.pipeline import build_pipeline
from betting.graph.state import BettingState
from betting.interfaces.stats_provider import IStatsProvider
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot
from betting.services.fixture_service import FixtureService
from betting.services.ledger_service import LedgerService
from betting.services.statistical_service import StatisticalService


def _stub_fixture() -> Fixture:
    return Fixture(
        id="fix-pipeline-001",
        home_team="Arsenal",
        away_team="Chelsea",
        league="PL",
        season="2024/25",
        matchday=30,
        kickoff=datetime(2025, 4, 1, 15, 0, tzinfo=timezone.utc),
    )


def _stub_odds() -> OddsSnapshot:
    return OddsSnapshot(
        fixture_id="fix-pipeline-001",
        market="double_chance",
        bookmaker="stub",
        home_draw=1.80,
        home_away=1.60,
        draw_away=2.50,
        fetched_at=datetime.now(tz=timezone.utc),
    )


def _make_stats_provider(
    home_attack=1.2, home_defence=0.9,
    away_attack=0.9, away_defence=1.1,
    avg_home=1.5, avg_away=1.2,
) -> IStatsProvider:
    provider = MagicMock(spec=IStatsProvider)
    provider.get_attack_defence_ratings.return_value = (
        home_attack, home_defence, away_attack, away_defence
    )
    provider.get_league_averages.return_value = (avg_home, avg_away)
    return provider


@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "test_ledger.db")


@pytest.fixture()
def pipeline(db_path):
    fixture_service = MagicMock(spec=FixtureService)
    statistical_service = StatisticalService(stats_provider=_make_stats_provider())
    ledger_repo = SqliteLedgerRepository(db_path=db_path)
    ledger_service = LedgerService(repository=ledger_repo)

    return build_pipeline(
        ingest_node=IngestNode(fixture_service),
        statistical_node=StatisticalNode(statistical_service),
        synthesiser_node=SynthesiserNode(),
        ledger_node=LedgerNode(ledger_service),
    ), ledger_repo


class TestPipelineEndToEnd:
    def test_eligible_fixture_recorded(self, pipeline):
        graph, ledger_repo = pipeline
        fixture = _stub_fixture()
        odds = _stub_odds()

        initial_state: BettingState = {
            "fixture": asdict(fixture),
            "markets": ["double_chance"],
            "odds_snapshot": asdict(odds),
            "eligible": True,
            "statistical_signal": None,
            "verdict": None,
            "recorded": False,
            "errors": [],
        }

        final_state = graph.invoke(initial_state)

        assert final_state["recorded"] is True
        assert final_state["errors"] == []

        record = ledger_repo.get_by_fixture("fix-pipeline-001")
        assert record is not None

    def test_ineligible_fixture_skipped_to_ledger(self, pipeline):
        graph, ledger_repo = pipeline
        fixture = _stub_fixture()
        odds = _stub_odds()

        initial_state: BettingState = {
            "fixture": asdict(fixture),
            "markets": ["double_chance"],
            "odds_snapshot": asdict(odds),
            "eligible": False,  # pre-marked ineligible
            "statistical_signal": None,
            "verdict": None,
            "recorded": False,
            "errors": [],
        }

        final_state = graph.invoke(initial_state)

        # Should still be recorded (as a skip)
        assert final_state["recorded"] is True

    def test_statistical_signal_populated_for_eligible_fixture(self, pipeline):
        graph, _ = pipeline
        fixture = _stub_fixture()
        odds = _stub_odds()

        initial_state: BettingState = {
            "fixture": asdict(fixture),
            "markets": ["double_chance"],
            "odds_snapshot": asdict(odds),
            "eligible": True,
            "statistical_signal": None,
            "verdict": None,
            "recorded": False,
            "errors": [],
        }

        final_state = graph.invoke(initial_state)

        assert final_state["statistical_signal"] is not None
        assert final_state["statistical_signal"]["agent_id"] == "statistical"

    def test_verdict_populated_after_synthesis(self, pipeline):
        graph, _ = pipeline
        fixture = _stub_fixture()
        odds = _stub_odds()

        initial_state: BettingState = {
            "fixture": asdict(fixture),
            "markets": ["double_chance"],
            "odds_snapshot": asdict(odds),
            "eligible": True,
            "statistical_signal": None,
            "verdict": None,
            "recorded": False,
            "errors": [],
        }

        final_state = graph.invoke(initial_state)

        assert final_state["verdict"] is not None
        assert final_state["verdict"]["fixture_id"] == "fix-pipeline-001"
        assert final_state["verdict"]["recommendation"] in ("back", "lay", "skip")

    def test_no_errors_in_happy_path(self, pipeline):
        graph, _ = pipeline
        fixture = _stub_fixture()
        odds = _stub_odds()

        initial_state: BettingState = {
            "fixture": asdict(fixture),
            "markets": ["double_chance"],
            "odds_snapshot": asdict(odds),
            "eligible": True,
            "statistical_signal": None,
            "verdict": None,
            "recorded": False,
            "errors": [],
        }

        final_state = graph.invoke(initial_state)
        assert final_state["errors"] == []
