import os
from dataclasses import dataclass

import yaml


_DEFAULT_YAML_PATH = os.environ.get("BETTING_LEAGUES_CONFIG", "config/leagues.yaml")


@dataclass(frozen=True)
class LeagueEntry:
    id: str
    football_data_code: str
    odds_api_key: str
    active: bool
    team_names: dict  # football-data name -> Odds API name


class LeagueConfigLoader:
    def __init__(self, yaml_path: str = _DEFAULT_YAML_PATH) -> None:
        with open(yaml_path, encoding="utf-8") as f:
            raw: dict = yaml.safe_load(f)

        self._leagues: dict[str, LeagueEntry] = {}
        for league_id, data in raw.items():
            self._leagues[league_id] = LeagueEntry(
                id=league_id,
                football_data_code=data["football_data_code"],
                odds_api_key=data["odds_api_key"],
                active=bool(data.get("active", False)),
                team_names=dict(data.get("team_names") or {}),
            )

    def active_leagues(self) -> list[LeagueEntry]:
        """Returns only leagues where active=true."""
        return [entry for entry in self._leagues.values() if entry.active]

    def get(self, league_id: str) -> LeagueEntry | None:
        """Returns entry for a specific league id, or None."""
        return self._leagues.get(league_id)

    def football_data_code(self, league_id: str) -> str | None:
        entry = self._leagues.get(league_id)
        return entry.football_data_code if entry else None

    def odds_api_key(self, league_id: str) -> str | None:
        entry = self._leagues.get(league_id)
        return entry.odds_api_key if entry else None

    def team_names(self, league_id: str) -> dict[str, str]:
        """Returns team name map for league, empty dict if not found."""
        entry = self._leagues.get(league_id)
        return dict(entry.team_names) if entry else {}
