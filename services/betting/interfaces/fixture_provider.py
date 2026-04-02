from abc import ABC, abstractmethod
from betting.models.fixture import Fixture


class IFixtureProvider(ABC):
    @abstractmethod
    def fetch_upcoming(
        self,
        leagues: list[str],
        days_ahead: int = 2,
    ) -> list[Fixture]:
        ...
