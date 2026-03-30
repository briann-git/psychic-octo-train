"""Tests for MarketConfigLoader — mirrors test_league_config.py pattern."""

import os
import tempfile

import pytest
import yaml

from betting.config.market_config import (
    MarketConfigLoader,
    MarketDefinition,
    SelectionDefinition,
)


_SAMPLE_YAML = {
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
    "btts": {
        "active": False,
        "odds_api_market_key": "btts",
        "odds_derivation": "direct",
        "evaluation_strategy": "btts",
        "settlement_source": "api",
        "selections": [
            {"id": "yes", "label": "Both Teams to Score", "wins_if": "btts_yes"},
            {"id": "no", "label": "Neither Team to Score", "wins_if": "btts_no"},
        ],
    },
    "over_under_25": {
        "active": False,
        "odds_api_market_key": "totals",
        "odds_derivation": "direct",
        "evaluation_strategy": "total",
        "settlement_source": "api",
        "selections": [
            {
                "id": "over_25",
                "label": "Over 2.5 Goals",
                "wins_if": {"columns": ["fthg", "ftag"], "operator": ">", "threshold": 2.5},
            },
            {
                "id": "under_25",
                "label": "Under 2.5 Goals",
                "wins_if": {"columns": ["fthg", "ftag"], "operator": "<=", "threshold": 2.5},
            },
        ],
    },
}


@pytest.fixture()
def yaml_path(tmp_path):
    path = str(tmp_path / "markets.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(_SAMPLE_YAML, f)
    return path


@pytest.fixture()
def loader(yaml_path) -> MarketConfigLoader:
    return MarketConfigLoader(yaml_path=yaml_path)


class TestActiveMarkets:
    def test_returns_only_active_markets(self, loader):
        active = loader.active_markets()
        assert len(active) == 1
        assert active[0].id == "double_chance"

    def test_inactive_market_not_included(self, loader):
        active_ids = [m.id for m in loader.active_markets()]
        assert "btts" not in active_ids
        assert "over_under_25" not in active_ids


class TestGet:
    def test_returns_correct_market(self, loader):
        market = loader.get("double_chance")
        assert market is not None
        assert market.id == "double_chance"
        assert market.odds_api_market_key == "h2h"
        assert market.odds_derivation == "implied_sum"
        assert market.active is True
        assert market.evaluation_strategy == "ftr"
        assert market.settlement_source == "api"

    def test_returns_none_for_unknown_market(self, loader):
        assert loader.get("nonexistent") is None

    def test_returns_inactive_market(self, loader):
        market = loader.get("btts")
        assert market is not None
        assert market.active is False


class TestSelections:
    def test_double_chance_has_three_selections(self, loader):
        market = loader.get("double_chance")
        assert len(market.selections) == 3

    def test_selection_ids_ordered(self, loader):
        ids = loader.selection_ids("double_chance")
        assert ids == ["1X", "12", "X2"]

    def test_selection_ids_empty_for_unknown(self, loader):
        assert loader.selection_ids("nonexistent") == []

    def test_get_selection_returns_correct_entry(self, loader):
        sel = loader.get_selection("double_chance", "1X")
        assert sel is not None
        assert sel.id == "1X"
        assert sel.label == "Home or Draw"
        assert sel.wins_if == "H | D"
        assert sel.evaluation_strategy == "ftr"

    def test_get_selection_returns_none_for_unknown_selection(self, loader):
        assert loader.get_selection("double_chance", "UNKNOWN") is None

    def test_get_selection_returns_none_for_unknown_market(self, loader):
        assert loader.get_selection("nonexistent", "1X") is None

    def test_total_selection_has_dict_wins_if(self, loader):
        sel = loader.get_selection("over_under_25", "over_25")
        assert isinstance(sel.wins_if, dict)
        assert sel.wins_if["columns"] == ["fthg", "ftag"]
        assert sel.wins_if["operator"] == ">"
        assert sel.wins_if["threshold"] == 2.5


class TestOddsApiMarketKey:
    def test_returns_key_for_known_market(self, loader):
        assert loader.odds_api_market_key("double_chance") == "h2h"

    def test_returns_none_for_unknown_market(self, loader):
        assert loader.odds_api_market_key("nonexistent") is None


class TestOddsDerivedMethod:
    def test_implied_sum_for_double_chance(self, loader):
        assert loader.odds_derivation("double_chance") == "implied_sum"

    def test_direct_for_btts(self, loader):
        assert loader.odds_derivation("btts") == "direct"

    def test_direct_for_unknown(self, loader):
        assert loader.odds_derivation("nonexistent") == "direct"


class TestSettlementSource:
    def test_returns_api_for_double_chance(self, loader):
        assert loader.settlement_source("double_chance") == "api"

    def test_returns_api_for_unknown(self, loader):
        assert loader.settlement_source("nonexistent") == "api"


class TestDefaultYamlPath:
    def test_loads_from_default_path(self):
        loader = MarketConfigLoader()
        market = loader.get("double_chance")
        assert market is not None
        assert market.active is True
