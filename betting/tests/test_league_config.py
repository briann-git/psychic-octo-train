"""Tests for LeagueConfigLoader."""

import textwrap

import pytest

from betting.config.league_config import LeagueConfigLoader


@pytest.fixture()
def yaml_path(tmp_path):
    content = textwrap.dedent("""\
        PL:
          football_data_code: "E0"
          odds_api_key: "soccer_epl"
          active: true
          team_names:
            "Man United": "Manchester United"
            "Man City": "Manchester City"
        La_Liga:
          football_data_code: "SP1"
          odds_api_key: "soccer_spain_la_liga"
          active: false
          team_names: {}
        Bundesliga:
          football_data_code: "D1"
          odds_api_key: "soccer_germany_bundesliga"
          active: false
          team_names: {}
    """)
    path = tmp_path / "leagues.yaml"
    path.write_text(content, encoding="utf-8")
    return str(path)


@pytest.fixture()
def loader(yaml_path):
    return LeagueConfigLoader(yaml_path=yaml_path)


class TestActiveLeagues:
    def test_returns_only_active_leagues(self, loader):
        active = loader.active_leagues()
        assert len(active) == 1
        assert active[0].id == "PL"

    def test_inactive_league_not_included(self, loader):
        ids = [l.id for l in loader.active_leagues()]
        assert "La_Liga" not in ids
        assert "Bundesliga" not in ids


class TestGet:
    def test_returns_correct_entry(self, loader):
        entry = loader.get("PL")
        assert entry is not None
        assert entry.id == "PL"
        assert entry.football_data_code == "E0"
        assert entry.odds_api_key == "soccer_epl"
        assert entry.active is True

    def test_returns_none_for_unknown_league(self, loader):
        assert loader.get("UnknownLeague") is None

    def test_returns_inactive_league(self, loader):
        entry = loader.get("La_Liga")
        assert entry is not None
        assert entry.active is False


class TestFootballDataCode:
    def test_returns_code_for_known_league(self, loader):
        assert loader.football_data_code("PL") == "E0"
        assert loader.football_data_code("La_Liga") == "SP1"

    def test_returns_none_for_unknown_league(self, loader):
        assert loader.football_data_code("UnknownLeague") is None


class TestOddsApiKey:
    def test_returns_key_for_known_league(self, loader):
        assert loader.odds_api_key("PL") == "soccer_epl"

    def test_returns_none_for_unknown_league(self, loader):
        assert loader.odds_api_key("UnknownLeague") is None


class TestTeamNames:
    def test_returns_team_names_for_pl(self, loader):
        names = loader.team_names("PL")
        assert names["Man United"] == "Manchester United"
        assert names["Man City"] == "Manchester City"

    def test_returns_empty_dict_for_no_mappings(self, loader):
        names = loader.team_names("La_Liga")
        assert names == {}

    def test_returns_empty_dict_for_unknown_league(self, loader):
        names = loader.team_names("UnknownLeague")
        assert names == {}


class TestDefaultYamlPath:
    def test_loads_from_default_path(self):
        loader = LeagueConfigLoader()
        # Default path should have PL as active
        entry = loader.get("PL")
        assert entry is not None
        assert entry.football_data_code == "E0"
        assert entry.active is True
