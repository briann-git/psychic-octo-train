from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OddsSnapshot:
    fixture_id: str
    market: str
    bookmaker: str
    home_draw: float   # 1X odds
    home_away: float   # 12 odds
    draw_away: float   # X2 odds
    fetched_at: datetime

    @classmethod
    def from_dict(cls, data: dict) -> "OddsSnapshot":
        d = dict(data)
        if isinstance(d.get("fetched_at"), str):
            d["fetched_at"] = datetime.fromisoformat(d["fetched_at"])
        return cls(**d)
