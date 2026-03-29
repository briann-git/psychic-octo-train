from abc import ABC, abstractmethod
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot


class IOddsProvider(ABC):
    @abstractmethod
    def fetch_odds(
        self,
        fixture: Fixture,
        markets: list[str],
    ) -> OddsSnapshot | None:
        ...
