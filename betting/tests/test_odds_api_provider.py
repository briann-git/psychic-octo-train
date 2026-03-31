import yaml

from betting.adapters.odds_api import OddsApiProvider
from betting.config.market_config import MarketConfigLoader


def _market_loader_with_direct_markets(tmp_path) -> MarketConfigLoader:
    config = {
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
                    "wins_if": {
                        "columns": ["fthg", "ftag"],
                        "operator": ">",
                        "threshold": 2.5,
                    },
                },
                {
                    "id": "under_25",
                    "label": "Under 2.5 Goals",
                    "outcome_name": "Under",
                    "outcome_point": 2.5,
                    "wins_if": {
                        "columns": ["fthg", "ftag"],
                        "operator": "<=",
                        "threshold": 2.5,
                    },
                },
            ],
        },
        "cards_over_under_35": {
            "active": False,
            "odds_api_market_key": "player_cards",
            "odds_derivation": "direct",
            "evaluation_strategy": "total",
            "settlement_source": "csv",
            "selections": [
                {
                    "id": "over_35",
                    "label": "Over 3.5 Cards",
                    "outcome_name": "Over",
                    "outcome_point": 3.5,
                    "wins_if": {
                        "columns": ["hy", "ay", "hr", "ar"],
                        "operator": ">",
                        "threshold": 3.5,
                    },
                },
                {
                    "id": "under_35",
                    "label": "Under 3.5 Cards",
                    "outcome_name": "Under",
                    "outcome_point": 3.5,
                    "wins_if": {
                        "columns": ["hy", "ay", "hr", "ar"],
                        "operator": "<=",
                        "threshold": 3.5,
                    },
                },
            ],
        },
        "btts": {
            "active": False,
            "odds_api_market_key": "btts",
            "odds_derivation": "direct",
            "evaluation_strategy": "btts",
            "settlement_source": "api",
            "selections": [
                {"id": "yes", "label": "Yes", "wins_if": "btts_yes"},
                {"id": "no", "label": "No", "wins_if": "btts_no"},
            ],
        },
    }

    yaml_path = tmp_path / "markets.yaml"
    yaml_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return MarketConfigLoader(yaml_path=str(yaml_path))


def _provider(tmp_path) -> OddsApiProvider:
    return OddsApiProvider(
        api_key="test",
        market_loader=_market_loader_with_direct_markets(tmp_path),
    )


def test_direct_totals_market_resolves_over_under_25_by_point(tmp_path):
    provider = _provider(tmp_path)
    event = {
        "bookmakers": [
            {
                "key": "bet365",
                "markets": [
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "point": 1.5, "price": 1.33},
                            {"name": "Under", "point": 1.5, "price": 3.30},
                            {"name": "Over", "point": 2.5, "price": 1.95},
                            {"name": "Under", "point": 2.5, "price": 1.88},
                            {"name": "Over", "point": 3.5, "price": 3.10},
                            {"name": "Under", "point": 3.5, "price": 1.34},
                        ],
                    }
                ],
            }
        ]
    }

    snapshot = provider._build_odds_snapshot(event, "fixture-1", "goals_over_under_25")

    assert snapshot is not None
    assert snapshot.market == "goals_over_under_25"
    assert snapshot.selections["over_25"] == 1.95
    assert snapshot.selections["under_25"] == 1.88


def test_direct_cards_market_resolves_over_under_35_by_point(tmp_path):
    provider = _provider(tmp_path)
    event = {
        "bookmakers": [
            {
                "key": "bet365",
                "markets": [
                    {
                        "key": "player_cards",
                        "outcomes": [
                            {"name": "Over", "point": 2.5, "price": 1.45},
                            {"name": "Under", "point": 2.5, "price": 2.65},
                            {"name": "Over", "point": 3.5, "price": 2.20},
                            {"name": "Under", "point": 3.5, "price": 1.67},
                        ],
                    }
                ],
            }
        ]
    }

    snapshot = provider._build_odds_snapshot(event, "fixture-2", "cards_over_under_35")

    assert snapshot is not None
    assert snapshot.market == "cards_over_under_35"
    assert snapshot.selections["over_35"] == 2.20
    assert snapshot.selections["under_35"] == 1.67


def test_direct_market_label_fallback_still_works_for_legacy_selections(tmp_path):
    provider = _provider(tmp_path)
    event = {
        "bookmakers": [
            {
                "key": "bet365",
                "markets": [
                    {
                        "key": "btts",
                        "outcomes": [
                            {"name": "Yes", "price": 1.80},
                            {"name": "No", "price": 1.95},
                        ],
                    }
                ],
            }
        ]
    }

    snapshot = provider._build_odds_snapshot(event, "fixture-3", "btts")

    assert snapshot is not None
    assert snapshot.market == "btts"
    assert snapshot.selections["yes"] == 1.80
    assert snapshot.selections["no"] == 1.95