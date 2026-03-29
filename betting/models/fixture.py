from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Fixture:
    id: str
    home_team: str
    away_team: str
    league: str
    season: str
    matchday: int
    kickoff: datetime
    venue: str | None = None
