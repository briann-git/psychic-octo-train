"""Tests for FootballDataProvider."""

import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from betting.adapters.football_data import (
    FootballDataProvider,
    MIN_GAMES_THRESHOLD,
)
from betting.models.fixture import Fixture


def _make_fixture(home_team: str = "Arsenal", away_team: str = "Chelsea") -> Fixture:
    return Fixture(
        id="fix-001",
        home_team=home_team,
        away_team=away_team,
        league="PL",
        season="2024/25",
        matchday=30,
        kickoff=datetime(2025, 4, 1, 15, 0, tzinfo=timezone.utc),
    )


def _write_csv(rows: list[dict], bom: bool = False) -> str:
    """Write a minimal football-data CSV to a temp file and return its path."""
    fd, path = tempfile.mkstemp(suffix=".csv")
    encoding = "utf-8-sig" if bom else "utf-8"
    with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
        f.write("HomeTeam,AwayTeam,FTHG,FTAG\n")
        for row in rows:
            f.write(f"{row['HomeTeam']},{row['AwayTeam']},{row['FTHG']},{row['FTAG']}\n")
    return path


def _make_provider(csv_path: str) -> FootballDataProvider:
    csv_service = MagicMock()
    csv_service.get.return_value = csv_path
    return FootballDataProvider(csv_service=csv_service)


def _enough_rows(home_team: str, away_team: str, n: int = MIN_GAMES_THRESHOLD) -> list[dict]:
    """Generate enough rows so both teams have >= MIN_GAMES_THRESHOLD home and away games."""
    rows = []
    for _ in range(n):
        rows.append({"HomeTeam": home_team, "AwayTeam": away_team, "FTHG": 2, "FTAG": 1})
        rows.append({"HomeTeam": away_team, "AwayTeam": home_team, "FTHG": 1, "FTAG": 1})
    return rows


class TestLeagueAverages:
    def test_correct_league_average_computation(self):
        rows = [
            {"HomeTeam": "Arsenal", "AwayTeam": "Chelsea", "FTHG": 2, "FTAG": 1},
            {"HomeTeam": "Chelsea", "AwayTeam": "Arsenal", "FTHG": 3, "FTAG": 0},
        ]
        path = _write_csv(rows)
        try:
            provider = _make_provider(path)
            avg_home, avg_away = provider.get_league_averages("PL", "2024/25")
            # home goals: 2 + 3 = 5 / 2 rows = 2.5
            # away goals: 1 + 0 = 1 / 2 rows = 0.5
            assert avg_home == pytest.approx(2.5)
            assert avg_away == pytest.approx(0.5)
        finally:
            os.unlink(path)

    def test_unsupported_league_returns_defaults(self):
        provider = _make_provider("/nonexistent.csv")
        avg_home, avg_away = provider.get_league_averages("UnknownLeague", "2024/25")
        assert avg_home == pytest.approx(1.5)
        assert avg_away == pytest.approx(1.2)


class TestAttackDefenceRatings:
    def test_correct_ratings_for_team_with_sufficient_games(self):
        rows = _enough_rows("Arsenal", "Chelsea")
        path = _write_csv(rows)
        try:
            provider = _make_provider(path)
            fixture = _make_fixture("Arsenal", "Chelsea")
            home_attack, home_defence, away_attack, away_defence = (
                provider.get_attack_defence_ratings(fixture)
            )
            # All values should be positive floats, not necessarily 1.0
            assert home_attack > 0
            assert home_defence > 0
            assert away_attack > 0
            assert away_defence > 0
        finally:
            os.unlink(path)

    def test_rating_formula_correctness(self):
        # Arsenal always scores 2 at home, concedes 1
        # Chelsea always scores 1 at home, concedes 2
        # Arsenal always scores 1 away, concedes 1
        # Chelsea always scores 1 away, concedes 2
        n = MIN_GAMES_THRESHOLD
        rows = []
        for _ in range(n):
            rows.append({"HomeTeam": "Arsenal", "AwayTeam": "Chelsea", "FTHG": 2, "FTAG": 1})
            rows.append({"HomeTeam": "Chelsea", "AwayTeam": "Arsenal", "FTHG": 1, "FTAG": 1})
        path = _write_csv(rows)
        try:
            provider = _make_provider(path)
            # Total rows = 2*n, home goals = n*2 + n*1 = 3n, away goals = n*1 + n*1 = 2n
            avg_home = 3 * n / (2 * n)   # = 1.5
            avg_away = 2 * n / (2 * n)   # = 1.0

            fixture = _make_fixture("Arsenal", "Chelsea")
            home_attack, home_defence, away_attack, away_defence = (
                provider.get_attack_defence_ratings(fixture)
            )
            # Arsenal home: scores 2/game -> 2 / avg_home = 2/1.5
            assert home_attack == pytest.approx(2.0 / avg_home)
            # Arsenal home defence: concedes 1/game -> 1 / avg_away = 1/1.0
            assert home_defence == pytest.approx(1.0 / avg_away)
            # Chelsea away: scores 1/game -> 1 / avg_away = 1/1.0
            assert away_attack == pytest.approx(1.0 / avg_away)
            # Chelsea away defence: concedes 2/game -> 2 / avg_home = 2/1.5
            assert away_defence == pytest.approx(2.0 / avg_home)
        finally:
            os.unlink(path)

    def test_fallback_to_1_when_below_threshold(self):
        # Only 1 game each for each team
        rows = [
            {"HomeTeam": "Arsenal", "AwayTeam": "Chelsea", "FTHG": 3, "FTAG": 0},
        ]
        path = _write_csv(rows)
        try:
            provider = _make_provider(path)
            fixture = _make_fixture("Arsenal", "Chelsea")
            home_attack, home_defence, away_attack, away_defence = (
                provider.get_attack_defence_ratings(fixture)
            )
            # Both teams have only 1 game (< MIN_GAMES_THRESHOLD=5), expect 1.0 fallbacks
            assert home_attack == pytest.approx(1.0)
            assert home_defence == pytest.approx(1.0)
            assert away_attack == pytest.approx(1.0)
            assert away_defence == pytest.approx(1.0)
        finally:
            os.unlink(path)

    def test_fallback_to_1_when_team_not_found(self):
        rows = _enough_rows("Arsenal", "Chelsea")
        path = _write_csv(rows)
        try:
            provider = _make_provider(path)
            fixture = _make_fixture("UnknownTeam", "AnotherUnknown")
            home_attack, home_defence, away_attack, away_defence = (
                provider.get_attack_defence_ratings(fixture)
            )
            assert home_attack == pytest.approx(1.0)
            assert home_defence == pytest.approx(1.0)
            assert away_attack == pytest.approx(1.0)
            assert away_defence == pytest.approx(1.0)
        finally:
            os.unlink(path)

    def test_unsupported_league_returns_1(self):
        provider = _make_provider("/nonexistent.csv")
        fixture = Fixture(
            id="fix-002",
            home_team="TeamA",
            away_team="TeamB",
            league="UnknownLeague",
            season="2024/25",
            matchday=1,
            kickoff=datetime(2025, 4, 1, 15, 0, tzinfo=timezone.utc),
        )
        result = provider.get_attack_defence_ratings(fixture)
        assert result == (1.0, 1.0, 1.0, 1.0)


class TestBomHandling:
    def test_bom_csv_is_parsed_correctly(self):
        rows = _enough_rows("Arsenal", "Chelsea")
        path = _write_csv(rows, bom=True)
        try:
            provider = _make_provider(path)
            avg_home, avg_away = provider.get_league_averages("PL", "2024/25")
            # Should parse without error
            assert avg_home > 0
            assert avg_away > 0
        finally:
            os.unlink(path)


class TestSkipUnplayedFixtures:
    def test_skips_rows_with_missing_fthg(self):
        fd, path = tempfile.mkstemp(suffix=".csv")
        n = MIN_GAMES_THRESHOLD
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write("HomeTeam,AwayTeam,FTHG,FTAG\n")
            # Unplayed fixture — empty goals
            f.write("Arsenal,Chelsea,,\n")
            # Played fixtures
            for _ in range(n):
                f.write(f"Arsenal,Chelsea,2,1\n")
                f.write(f"Chelsea,Arsenal,1,1\n")
        try:
            provider = _make_provider(path)
            avg_home, avg_away = provider.get_league_averages("PL", "2024/25")
            # Only n*2 rows with goals should be counted
            # home goals: 2*n + 1*n = 3n, away goals: 1*n + 1*n = 2n
            assert avg_home == pytest.approx(3 * n / (2 * n))
            assert avg_away == pytest.approx(2 * n / (2 * n))
        finally:
            os.unlink(path)


class TestTeamNameNormalisation:
    def test_normalises_man_united(self):
        n = MIN_GAMES_THRESHOLD
        rows = []
        for _ in range(n):
            rows.append({"HomeTeam": "Man United", "AwayTeam": "Chelsea", "FTHG": 2, "FTAG": 1})
            rows.append({"HomeTeam": "Chelsea", "AwayTeam": "Man United", "FTHG": 1, "FTAG": 1})
        path = _write_csv(rows)
        try:
            provider = _make_provider(path)
            # Look up using normalised name (The Odds API convention)
            fixture = _make_fixture("Manchester United", "Chelsea")
            home_attack, _, _, _ = provider.get_attack_defence_ratings(fixture)
            # Should find the team and not return 1.0 fallback
            # home goals for Man United: 2/game, league avg home computed from all rows
            assert home_attack > 0
            # Verify it's not the fallback 1.0 from missing team
            avg_home, _ = provider.get_league_averages("PL", "2024/25")
            expected_attack = 2.0 / avg_home
            assert home_attack == pytest.approx(expected_attack)
        finally:
            os.unlink(path)
