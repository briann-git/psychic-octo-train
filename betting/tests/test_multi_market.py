"""Tests for multi-market pipeline support.

Covers:
  - IOddsProvider.fetch_all_odds default implementation
  - OddsApiProvider.fetch_all_odds
  - FixtureService.get_eligible_fixtures_multi
  - SynthesiserNode / LedgerNode correct market derivation from odds_snapshot
  - End-to-end pipeline run with over/under market
"""

import yaml
from dataclasses import asdict
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from betting.adapters.odds_api import OddsApiProvider
from betting.adapters.sqlite_ledger import SqliteLedgerRepository
from betting.config.market_config import MarketConfigLoader
from betting.graph.nodes.ingest import IngestNode
from betting.graph.nodes.ledger import LedgerNode
from betting.graph.nodes.market import MarketNode
from betting.graph.nodes.statistical import StatisticalNode
from betting.graph.nodes.synthesiser import SynthesiserNode
from betting.graph.pipeline import build_pipeline
from betting.graph.state import BettingState
from betting.interfaces.odds_provider import IOddsProvider
from betting.interfaces.stats_provider import IStatsProvider
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot
from betting.models.signal import Signal
from betting.services.fixture_service import FixtureService
from betting.services.ledger_service import LedgerService
from betting.services.market_service import MarketService
from betting.services.statistical_service import StatisticalService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fixture(fixture_id: str = "fix-multi-001") -> Fixture:
    return Fixture(
        id=fixture_id,
        home_team="Arsenal",
        away_team="Chelsea",
        league="PL",
        season="2024/25",
        matchday=30,
        kickoff=datetime(2025, 4, 1, 15, 0, tzinfo=timezone.utc),
    )


def _dc_odds(fixture_id: str = "fix-multi-001") -> OddsSnapshot:
    return OddsSnapshot(
        fixture_id=fixture_id,
        market="double_chance",
        bookmaker="stub",
        selections={"1X": 1.80, "12": 1.60, "X2": 2.50},
        fetched_at=datetime.now(tz=timezone.utc),
    )


def _ou_odds(fixture_id: str = "fix-multi-001") -> OddsSnapshot:
    return OddsSnapshot(
        fixture_id=fixture_id,
        market="goals_over_under_25",
        bookmaker="stub",
        selections={"over_25": 1.95, "under_25": 1.88},
        fetched_at=datetime.now(tz=timezone.utc),
    )


def _make_stats_provider() -> IStatsProvider:
    provider = MagicMock(spec=IStatsProvider)
    provider.get_attack_defence_ratings.return_value = (1.2, 0.9, 0.9, 1.1)
    provider.get_league_averages.return_value = (1.5, 1.2)
    return provider


def _make_signal(agent_id: str = "statistical", selection: str = "1X") -> dict:
    return asdict(Signal(
        agent_id=agent_id,
        fixture_id="fix-multi-001",
        recommendation="back",
        confidence=0.75,
        edge=0.10,
        reasoning="test",
        data_timestamp=datetime.now(tz=timezone.utc),
        selection=selection,
    ))


# ---------------------------------------------------------------------------
# IOddsProvider.fetch_all_odds — default implementation
# ---------------------------------------------------------------------------

class TestFetchAllOddsDefault:
    """The base class default implementation should call fetch_odds per market."""

    def test_returns_snapshot_per_market(self):
        class _StubProvider(IOddsProvider):
            def fetch_odds(self, fixture, markets):
                mid = markets[0]
                if mid == "double_chance":
                    return _dc_odds(fixture.id)
                if mid == "goals_over_under_25":
                    return _ou_odds(fixture.id)
                return None

        provider = _StubProvider()
        results = provider.fetch_all_odds(
            _fixture(), ["double_chance", "goals_over_under_25"]
        )
        assert len(results) == 2
        assert results[0].market == "double_chance"
        assert results[1].market == "goals_over_under_25"

    def test_skips_markets_with_no_odds(self):
        class _StubProvider(IOddsProvider):
            def fetch_odds(self, fixture, markets):
                if markets[0] == "double_chance":
                    return _dc_odds(fixture.id)
                return None

        provider = _StubProvider()
        results = provider.fetch_all_odds(
            _fixture(), ["double_chance", "goals_over_under_25"]
        )
        assert len(results) == 1
        assert results[0].market == "double_chance"

    def test_empty_when_no_odds_available(self):
        class _StubProvider(IOddsProvider):
            def fetch_odds(self, fixture, markets):
                return None

        provider = _StubProvider()
        results = provider.fetch_all_odds(
            _fixture(), ["double_chance", "goals_over_under_25"]
        )
        assert results == []


# ---------------------------------------------------------------------------
# OddsApiProvider.fetch_all_odds
# ---------------------------------------------------------------------------

class TestOddsApiProviderFetchAllOdds:
    def _market_loader(self, tmp_path) -> MarketConfigLoader:
        config = {
            "double_chance": {
                "active": True,
                "odds_api_market_key": "h2h",
                "odds_derivation": "implied_sum",
                "evaluation_strategy": "ftr",
                "settlement_source": "api",
                "selections": [
                    {"id": "1X", "label": "Home or Draw", "wins_if": "H | D"},
                    {"id": "12", "label": "Home or Away", "wins_if": "H | A"},
                    {"id": "X2", "label": "Draw or Away", "wins_if": "D | A"},
                ],
            },
            "goals_over_under_25": {
                "active": True,
                "odds_api_market_key": "totals",
                "odds_derivation": "direct",
                "evaluation_strategy": "total",
                "settlement_source": "api",
                "selections": [
                    {
                        "id": "over_25",
                        "label": "Over 2.5 Goals",
                        "outcome_name": "Over",
                        "outcome_point": 2.5,
                        "wins_if": {"columns": ["fthg", "ftag"], "operator": ">", "threshold": 2.5},
                    },
                    {
                        "id": "under_25",
                        "label": "Under 2.5 Goals",
                        "outcome_name": "Under",
                        "outcome_point": 2.5,
                        "wins_if": {"columns": ["fthg", "ftag"], "operator": "<=", "threshold": 2.5},
                    },
                ],
            },
        }
        yaml_path = tmp_path / "markets.yaml"
        yaml_path.write_text(yaml.safe_dump(config), encoding="utf-8")
        return MarketConfigLoader(yaml_path=str(yaml_path))

    def test_returns_snapshots_for_both_markets(self, tmp_path):
        loader = self._market_loader(tmp_path)
        provider = OddsApiProvider(api_key="test", market_loader=loader)

        event = {
            "id": "fix-1",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "bookmakers": [
                {
                    "key": "bet365",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Arsenal", "price": 2.10},
                                {"name": "Draw", "price": 3.40},
                                {"name": "Chelsea", "price": 3.20},
                            ],
                        },
                        {
                            "key": "totals",
                            "outcomes": [
                                {"name": "Over", "point": 2.5, "price": 1.95},
                                {"name": "Under", "point": 2.5, "price": 1.88},
                            ],
                        },
                    ],
                }
            ],
        }

        # Inject the event into the cache to avoid real HTTP calls
        provider._cache["soccer_epl"] = [event]

        fixture = Fixture(
            id="fix-1",
            home_team="Arsenal",
            away_team="Chelsea",
            league="PL",
            season="2024/25",
            matchday=30,
            kickoff=datetime(2025, 4, 1, 15, 0, tzinfo=timezone.utc),
        )

        # We need to mock the league loader too
        league_loader = MagicMock()
        league_loader.odds_api_key.return_value = "soccer_epl"
        provider._league_loader = league_loader

        snapshots = provider.fetch_all_odds(
            fixture, ["double_chance", "goals_over_under_25"]
        )

        assert len(snapshots) == 2
        markets_found = {s.market for s in snapshots}
        assert "double_chance" in markets_found
        assert "goals_over_under_25" in markets_found

    def test_returns_partial_when_one_market_unavailable(self, tmp_path):
        loader = self._market_loader(tmp_path)
        provider = OddsApiProvider(api_key="test", market_loader=loader)

        event = {
            "id": "fix-2",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "bookmakers": [
                {
                    "key": "bet365",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Arsenal", "price": 2.10},
                                {"name": "Draw", "price": 3.40},
                                {"name": "Chelsea", "price": 3.20},
                            ],
                        },
                        # No totals market
                    ],
                }
            ],
        }

        provider._cache["soccer_epl"] = [event]

        league_loader = MagicMock()
        league_loader.odds_api_key.return_value = "soccer_epl"
        provider._league_loader = league_loader

        fixture = Fixture(
            id="fix-2",
            home_team="Arsenal",
            away_team="Chelsea",
            league="PL",
            season="2024/25",
            matchday=30,
            kickoff=datetime(2025, 4, 1, 15, 0, tzinfo=timezone.utc),
        )

        snapshots = provider.fetch_all_odds(
            fixture, ["double_chance", "goals_over_under_25"]
        )

        assert len(snapshots) == 1
        assert snapshots[0].market == "double_chance"


# ---------------------------------------------------------------------------
# FixtureService.get_eligible_fixtures_multi
# ---------------------------------------------------------------------------

class TestGetEligibleFixturesMulti:
    def test_returns_multiple_odds_per_fixture(self):
        fixture = _fixture()
        fixture_provider = MagicMock()
        fixture_provider.fetch_upcoming.return_value = [fixture]

        odds_provider = MagicMock()
        odds_provider.fetch_all_odds.return_value = [_dc_odds(), _ou_odds()]

        now = datetime.now(tz=timezone.utc)
        # Set fixture kickoff to be within the lead-time window
        fixture_in_window = Fixture(
            id="fix-multi-001",
            home_team="Arsenal",
            away_team="Chelsea",
            league="PL",
            season="2024/25",
            matchday=30,
            kickoff=now + timedelta(hours=10),
        )
        fixture_provider.fetch_upcoming.return_value = [fixture_in_window]

        service = FixtureService(
            fixture_provider=fixture_provider,
            odds_provider=odds_provider,
            supported_leagues=["PL"],
            min_lead_hours=2,
            max_lead_hours=48,
        )

        results = service.get_eligible_fixtures_multi(
            markets=["double_chance", "goals_over_under_25"],
        )

        assert len(results) == 1
        fix, odds_list = results[0]
        assert fix.id == "fix-multi-001"
        assert len(odds_list) == 2

    def test_excludes_fixture_with_no_odds_for_any_market(self):
        now = datetime.now(tz=timezone.utc)
        fixture_in_window = Fixture(
            id="fix-no-odds",
            home_team="A",
            away_team="B",
            league="PL",
            season="2024/25",
            matchday=1,
            kickoff=now + timedelta(hours=10),
        )
        fixture_provider = MagicMock()
        fixture_provider.fetch_upcoming.return_value = [fixture_in_window]

        odds_provider = MagicMock()
        odds_provider.fetch_all_odds.return_value = []

        service = FixtureService(
            fixture_provider=fixture_provider,
            odds_provider=odds_provider,
            supported_leagues=["PL"],
        )

        results = service.get_eligible_fixtures_multi(markets=["double_chance"])
        assert results == []


# ---------------------------------------------------------------------------
# SynthesiserNode market derivation from odds_snapshot
# ---------------------------------------------------------------------------

class TestSynthesiserMarketDerivation:
    def test_verdict_uses_market_from_odds_snapshot(self):
        node = SynthesiserNode(
            weights={"statistical": 0.60, "market": 0.40},
            confidence_threshold=0.60,
        )
        state: BettingState = {
            "fixture": {"id": "fix-syn-multi"},
            "markets": ["double_chance", "goals_over_under_25"],
            "odds_snapshot": {"market": "goals_over_under_25"},
            "eligible": True,
            "statistical_signal": _make_signal("statistical", "over_25"),
            "market_signal": _make_signal("market", "over_25"),
            "verdict": None,
            "recorded": False,
            "errors": [],
        }

        result = node(state)
        assert result["verdict"]["market"] == "goals_over_under_25"

    def test_verdict_falls_back_to_markets_list_when_no_snapshot_market(self):
        node = SynthesiserNode(
            weights={"statistical": 0.60, "market": 0.40},
            confidence_threshold=0.60,
        )
        state: BettingState = {
            "fixture": {"id": "fix-syn-fallback"},
            "markets": ["double_chance"],
            "odds_snapshot": {},
            "eligible": True,
            "statistical_signal": _make_signal(),
            "market_signal": None,
            "verdict": None,
            "recorded": False,
            "errors": [],
        }

        result = node(state)
        assert result["verdict"]["market"] == "double_chance"


# ---------------------------------------------------------------------------
# LedgerNode market derivation from odds_snapshot
# ---------------------------------------------------------------------------

class TestLedgerNodeMarketDerivation:
    def test_stub_verdict_uses_market_from_odds_snapshot(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        ledger_repo = SqliteLedgerRepository(db_path=db_path)
        ledger_service = LedgerService(repository=ledger_repo)
        node = LedgerNode(ledger_service)

        state: BettingState = {
            "fixture": {"id": "fix-ledger-multi", "home_team": "A", "away_team": "B",
                        "league": "PL", "season": "2024/25", "matchday": 1,
                        "kickoff": datetime(2025, 4, 1, 15, 0, tzinfo=timezone.utc).isoformat(),
                        "venue": None},
            "markets": ["double_chance", "goals_over_under_25"],
            "odds_snapshot": {
                "fixture_id": "fix-ledger-multi",
                "market": "goals_over_under_25",
                "bookmaker": "stub",
                "selections": {"over_25": 1.95, "under_25": 1.88},
                "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
            },
            "eligible": False,
            "statistical_signal": None,
            "market_signal": None,
            "verdict": None,
            "recorded": False,
            "errors": ["ingest: fixture marked ineligible by runner"],
        }

        result = node(state)
        assert result["verdict"]["market"] == "goals_over_under_25"


# ---------------------------------------------------------------------------
# End-to-end: pipeline with over/under market
# ---------------------------------------------------------------------------

class TestPipelineMultiMarket:
    @pytest.fixture()
    def pipeline_and_repo(self, tmp_path):
        db_path = str(tmp_path / "test_multi.db")
        fixture_service = MagicMock(spec=FixtureService)
        statistical_service = StatisticalService(stats_provider=_make_stats_provider())
        ledger_repo = SqliteLedgerRepository(db_path=db_path)
        ledger_service = LedgerService(repository=ledger_repo)

        graph = build_pipeline(
            ingest_node=IngestNode(fixture_service),
            statistical_node=StatisticalNode(statistical_service),
            market_node=MarketNode(MarketService(ledger_repo=ledger_repo)),
            synthesiser_node=SynthesiserNode(
                weights={"statistical": 0.60, "market": 0.40},
                confidence_threshold=0.60,
            ),
            ledger_node=LedgerNode(ledger_service),
        )
        return graph, ledger_repo

    def test_over_under_market_runs_through_pipeline(self, pipeline_and_repo):
        graph, ledger_repo = pipeline_and_repo
        odds = _ou_odds()

        state: BettingState = {
            "fixture": asdict(_fixture()),
            "markets": ["double_chance", "goals_over_under_25"],
            "odds_snapshot": asdict(odds),
            "eligible": True,
            "statistical_signal": None,
            "market_signal": None,
            "verdict": None,
            "recorded": False,
            "errors": [],
        }

        final = graph.invoke(state)
        assert final["recorded"] is True
        assert final["verdict"]["market"] == "goals_over_under_25"

    def test_two_markets_produce_independent_verdicts(self, pipeline_and_repo):
        """Running the pipeline twice (once per market) should produce
        two independent verdicts with the correct market label."""
        graph, ledger_repo = pipeline_and_repo
        active_markets = ["double_chance", "goals_over_under_25"]

        verdicts = []
        for odds in [_dc_odds(), _ou_odds()]:
            state: BettingState = {
                "fixture": asdict(_fixture()),
                "markets": active_markets,
                "odds_snapshot": asdict(odds),
                "eligible": True,
                "statistical_signal": None,
                "market_signal": None,
                "verdict": None,
                "recorded": False,
                "errors": [],
            }
            final = graph.invoke(state)
            verdicts.append(final["verdict"])

        assert verdicts[0]["market"] == "double_chance"
        assert verdicts[1]["market"] == "goals_over_under_25"
        assert all(v["fixture_id"] == "fix-multi-001" for v in verdicts)
