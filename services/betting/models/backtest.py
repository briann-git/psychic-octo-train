from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BacktestConfig:
    league: str
    season: str
    date_from: datetime | None = None
    date_to: datetime | None = None


@dataclass
class BacktestEquityPoint:
    fixture_date: datetime
    home_team: str
    away_team: str
    market: str
    recommendation: str   # "back" | "skip"
    outcome: str | None   # "won" | "lost" | "void" | None (skip)
    bankroll: float       # aggregate bankroll across all agents after settlement


@dataclass
class BacktestResult:
    config: BacktestConfig
    fixtures_processed: int
    picks_made: int
    equity_curve: list[BacktestEquityPoint] = field(default_factory=list)
    pnl_summary: dict = field(default_factory=dict)
