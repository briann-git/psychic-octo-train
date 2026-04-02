from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OddsSnapshot:
    fixture_id: str
    market: str
    bookmaker: str
    selections: dict[str, float]    # selection_id -> decimal odds
    fetched_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "OddsSnapshot":
        d = dict(data)
        if isinstance(d.get("fetched_at"), str):
            d["fetched_at"] = datetime.fromisoformat(d["fetched_at"])
        return cls(**d)
