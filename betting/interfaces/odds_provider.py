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

    def fetch_all_odds(
        self,
        fixture: Fixture,
        markets: list[str],
    ) -> list[OddsSnapshot]:
        """Return an OddsSnapshot for every market that has available odds.

        Default implementation calls :meth:`fetch_odds` once per market.
        Subclasses may override for efficiency.
        """
        snapshots: list[OddsSnapshot] = []
        for market_id in markets:
            snapshot = self.fetch_odds(fixture, [market_id])
            if snapshot is not None:
                snapshots.append(snapshot)
        return snapshots
