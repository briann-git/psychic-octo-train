import csv
import logging
from dataclasses import dataclass

from betting.interfaces.stats_provider import IStatsProvider
from betting.models.fixture import Fixture

logger = logging.getLogger(__name__)

LEAGUE_CODES: dict[str, str] = {
    "PL":         "E0",
    "La_Liga":    "SP1",
    "Bundesliga": "D1",
    "Serie_A":    "I1",
    "Ligue_1":    "F1",
}

TEAM_NAME_MAP: dict[str, str] = {
    "Man United":     "Manchester United",
    "Man City":       "Manchester City",
    "Nott'm Forest":  "Nottingham Forest",
    "Wolves":         "Wolverhampton Wanderers",
    "Spurs":          "Tottenham Hotspur",
    "Leicester":      "Leicester City",
    "Leeds":          "Leeds United",
    "Ipswich":        "Ipswich Town",
    "Sunderland":     "Sunderland",
    "Newcastle":      "Newcastle United",
    "Brighton":       "Brighton and Hove Albion",
    "Brentford":      "Brentford",
    "Bournemouth":    "Bournemouth",
    "Fulham":         "Fulham",
    "Southampton":    "Southampton",
    "Everton":        "Everton",
}

MIN_GAMES_THRESHOLD = 5


@dataclass
class TeamRatings:
    home_attack: float
    home_defence: float
    away_attack: float
    away_defence: float
    home_games: int
    away_games: int


@dataclass
class SeasonRatings:
    league_avg_home: float
    league_avg_away: float
    teams: dict[str, TeamRatings]


class FootballDataProvider(IStatsProvider):
    def __init__(self, csv_service) -> None:
        self._csv_service = csv_service
        self._ratings_cache: dict[str, SeasonRatings] = {}

    def get_attack_defence_ratings(
        self, fixture: Fixture
    ) -> tuple[float, float, float, float]:
        """
        Returns (home_attack, home_defence, away_attack, away_defence).
        All values relative to league average (1.0 = average).
        Falls back to (1.0, 1.0, 1.0, 1.0) with a WARNING log if:
          - League not supported
          - Team not found in season data
          - Team has fewer than MIN_GAMES_THRESHOLD results
        """
        league = fixture.league
        season = fixture.season

        if league not in LEAGUE_CODES:
            logger.warning("League %r not in LEAGUE_CODES, returning 1.0 ratings", league)
            return 1.0, 1.0, 1.0, 1.0

        ratings = self._get_season_ratings(league, season)
        if ratings is None:
            return 1.0, 1.0, 1.0, 1.0

        home_team = fixture.home_team
        away_team = fixture.away_team

        home_r = ratings.teams.get(home_team)
        if home_r is None:
            logger.warning(
                "Home team %r not found in ratings for %s %s, returning 1.0",
                home_team, league, season,
            )
            home_attack, home_defence = 1.0, 1.0
        else:
            home_attack = home_r.home_attack
            home_defence = home_r.home_defence

        away_r = ratings.teams.get(away_team)
        if away_r is None:
            logger.warning(
                "Away team %r not found in ratings for %s %s, returning 1.0",
                away_team, league, season,
            )
            away_attack, away_defence = 1.0, 1.0
        else:
            away_attack = away_r.away_attack
            away_defence = away_r.away_defence

        return home_attack, home_defence, away_attack, away_defence

    def get_league_averages(
        self, league: str, season: str
    ) -> tuple[float, float]:
        """
        Returns (league_avg_home_goals, league_avg_away_goals).
        Derived from full season data for the given league/season.
        """
        if league not in LEAGUE_CODES:
            logger.warning("League %r not in LEAGUE_CODES, returning default averages", league)
            return 1.5, 1.2

        ratings = self._get_season_ratings(league, season)
        if ratings is None:
            return 1.5, 1.2

        return ratings.league_avg_home, ratings.league_avg_away

    def _get_season_ratings(self, league: str, season: str) -> SeasonRatings | None:
        cache_key = f"{league}_{season}"
        if cache_key in self._ratings_cache:
            return self._ratings_cache[cache_key]

        try:
            ratings = self._load_ratings(league, season)
            self._ratings_cache[cache_key] = ratings
            return ratings
        except Exception as exc:
            logger.warning("Failed to load ratings for %s %s: %s", league, season, exc)
            return None

    def _load_ratings(self, league: str, season: str) -> SeasonRatings:
        """
        Reads CSV via CsvDownloadService, parses into SeasonRatings.
        Skips rows with missing FTHG or FTAG (unplayed fixtures).
        Uses utf-8-sig encoding to handle BOM present in football-data CSVs.
        """
        csv_path = self._csv_service.get(league, season)
        logger.info("Loading ratings for %s %s from %s", league, season, csv_path)

        home_goals_by_team: dict[str, list[float]] = {}
        home_conceded_by_team: dict[str, list[float]] = {}
        away_goals_by_team: dict[str, list[float]] = {}
        away_conceded_by_team: dict[str, list[float]] = {}

        total_home_goals = 0.0
        total_away_goals = 0.0
        total_rows = 0

        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fthg_raw = row.get("FTHG", "").strip()
                ftag_raw = row.get("FTAG", "").strip()
                if not fthg_raw or not ftag_raw:
                    continue

                try:
                    fthg = float(fthg_raw)
                    ftag = float(ftag_raw)
                except ValueError:
                    continue

                home_team_raw = row.get("HomeTeam", "").strip()
                away_team_raw = row.get("AwayTeam", "").strip()

                home_team = TEAM_NAME_MAP.get(home_team_raw, home_team_raw)
                away_team = TEAM_NAME_MAP.get(away_team_raw, away_team_raw)

                home_goals_by_team.setdefault(home_team, []).append(fthg)
                home_conceded_by_team.setdefault(home_team, []).append(ftag)
                away_goals_by_team.setdefault(away_team, []).append(ftag)
                away_conceded_by_team.setdefault(away_team, []).append(fthg)

                total_home_goals += fthg
                total_away_goals += ftag
                total_rows += 1

        if total_rows == 0:
            raise ValueError(f"No completed fixtures found in CSV for {league} {season}")

        league_avg_home = total_home_goals / total_rows
        league_avg_away = total_away_goals / total_rows

        all_teams = set(home_goals_by_team) | set(away_goals_by_team)
        teams: dict[str, TeamRatings] = {}

        for team in all_teams:
            h_goals = home_goals_by_team.get(team, [])
            h_conceded = home_conceded_by_team.get(team, [])
            a_goals = away_goals_by_team.get(team, [])
            a_conceded = away_conceded_by_team.get(team, [])

            home_games = len(h_goals)
            away_games = len(a_goals)

            if home_games >= MIN_GAMES_THRESHOLD:
                home_attack = (sum(h_goals) / home_games) / league_avg_home
                home_defence = (sum(h_conceded) / home_games) / league_avg_away
            else:
                logger.debug(
                    "Team %r has %d home games (< %d), falling back to 1.0 for home ratings",
                    team, home_games, MIN_GAMES_THRESHOLD,
                )
                home_attack = 1.0
                home_defence = 1.0

            if away_games >= MIN_GAMES_THRESHOLD:
                away_attack = (sum(a_goals) / away_games) / league_avg_away
                away_defence = (sum(a_conceded) / away_games) / league_avg_home
            else:
                logger.debug(
                    "Team %r has %d away games (< %d), falling back to 1.0 for away ratings",
                    team, away_games, MIN_GAMES_THRESHOLD,
                )
                away_attack = 1.0
                away_defence = 1.0

            teams[team] = TeamRatings(
                home_attack=home_attack,
                home_defence=home_defence,
                away_attack=away_attack,
                away_defence=away_defence,
                home_games=home_games,
                away_games=away_games,
            )

        return SeasonRatings(
            league_avg_home=league_avg_home,
            league_avg_away=league_avg_away,
            teams=teams,
        )
