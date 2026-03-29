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
