from abc import ABC, abstractmethod
from betting.models.fixture import Fixture


class IStatsProvider(ABC):
    @abstractmethod
    def get_attack_defence_ratings(
        self,
        fixture: Fixture,
    ) -> tuple[float, float, float, float]:
        """
        Returns (home_attack, home_defence, away_attack, away_defence).
        Values are rated relative to the league average (1.0 = average).
        """
        ...

    @abstractmethod
    def get_league_averages(self, league: str, season: str) -> tuple[float, float]:
        """
        Returns (league_avg_home_goals, league_avg_away_goals).
        """
        ...
