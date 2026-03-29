from betting.interfaces.stats_provider import IStatsProvider
from betting.models.fixture import Fixture


class FBrefProvider(IStatsProvider):
    """
    Stub implementation — returns neutral (1.0) ratings and league averages.
    Replace with real FBref scraping / API calls in a later iteration.
    """

    def get_attack_defence_ratings(
        self, fixture: Fixture
    ) -> tuple[float, float, float, float]:
        # (home_attack, home_defence, away_attack, away_defence)
        # 1.0 means exactly league-average in each dimension.
        return 1.0, 1.0, 1.0, 1.0

    def get_league_averages(
        self, league: str, season: str
    ) -> tuple[float, float]:
        # (avg_home_goals, avg_away_goals) — neutral 1.5 / 1.2 as defaults.
        return 1.5, 1.2
