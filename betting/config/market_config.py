from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Union

import yaml

_DEFAULT_YAML_PATH = os.environ.get("BETTING_MARKETS_CONFIG", "config/markets.yaml")


@dataclass(frozen=True)
class SelectionDefinition:
    id: str
    label: str
    wins_if: Union[str, dict]    # str for ftr/btts, dict for total
    evaluation_strategy: str     # inherited from parent market
    outcome_name: str | None = None
    outcome_point: float | None = None


@dataclass(frozen=True)
class MarketDefinition:
    id: str
    odds_api_market_key: str
    odds_derivation: str
    active: bool
    evaluation_strategy: str     # "ftr" | "btts" | "total"
    settlement_source: str       # "api" | "csv"
    selections: tuple[SelectionDefinition, ...]


class MarketConfigLoader:
    def __init__(self, yaml_path: str = _DEFAULT_YAML_PATH) -> None:
        with open(yaml_path, encoding="utf-8") as f:
            raw: dict = yaml.safe_load(f)

        self._markets: dict[str, MarketDefinition] = {}
        for market_id, data in raw.items():
            strategy = data.get("evaluation_strategy", "ftr")
            selections = tuple(
                SelectionDefinition(
                    id=s["id"],
                    label=s["label"],
                    wins_if=s["wins_if"],       # passed through as-is
                    evaluation_strategy=strategy,
                    outcome_name=s.get("outcome_name"),
                    outcome_point=(
                        float(s["outcome_point"])
                        if s.get("outcome_point") is not None
                        else None
                    ),
                )
                for s in data.get("selections", [])
            )
            self._markets[market_id] = MarketDefinition(
                id=market_id,
                odds_api_market_key=data["odds_api_market_key"],
                odds_derivation=data.get("odds_derivation", "direct"),
                active=bool(data.get("active", False)),
                evaluation_strategy=strategy,
                settlement_source=data.get("settlement_source", "api"),
                selections=selections,
            )

    def active_markets(self) -> list[MarketDefinition]:
        """Returns only markets where active=true."""
        return [m for m in self._markets.values() if m.active]

    def get(self, market_id: str) -> MarketDefinition | None:
        return self._markets.get(market_id)

    def get_selection(
        self, market_id: str, selection_id: str
    ) -> SelectionDefinition | None:
        market = self._markets.get(market_id)
        if not market:
            return None
        return next((s for s in market.selections if s.id == selection_id), None)

    def selection_ids(self, market_id: str) -> list[str]:
        """Returns ordered list of selection ids for a market."""
        market = self._markets.get(market_id)
        return [s.id for s in market.selections] if market else []

    def odds_api_market_key(self, market_id: str) -> str | None:
        market = self._markets.get(market_id)
        return market.odds_api_market_key if market else None

    def odds_derivation(self, market_id: str) -> str:
        market = self._markets.get(market_id)
        return market.odds_derivation if market else "direct"

    def settlement_source(self, market_id: str) -> str:
        market = self._markets.get(market_id)
        return market.settlement_source if market else "api"
