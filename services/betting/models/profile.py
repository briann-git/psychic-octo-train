from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Profile:
    id: str
    name: str
    type: str  # "paper" | "live" | "backtest"
    bankroll_start: float = 1000.0
    is_active: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.min)
