from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from betting.models.fixture import Fixture


class IStatsProvider(ABC):
    @abstractmethod
    def get_attack_defence_ratings(
        self,
        fixture: Fixture,
        cutoff_date: Optional[datetime] = None,
    ) -> tuple[float, float, float, float]:
        """
        Returns (home_attack, home_defence, away_attack, away_defence).
        Values are rated relative to the league average (1.0 = average).
        If cutoff_date is provided, only match data before that date is used.
        """
        ...

    @abstractmethod
    def get_league_averages(
        self,
        league: str,
        season: str,
        cutoff_date: Optional[datetime] = None,
    ) -> tuple[float, float]:
        """
        Returns (league_avg_home_goals, league_avg_away_goals).
        If cutoff_date is provided, only match data before that date is used.
        """
        ...
