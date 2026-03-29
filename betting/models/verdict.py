from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class Verdict:
    fixture_id: str
    market: str
    recommendation: Literal["back", "lay", "skip"]
    consensus_confidence: float
    expected_value: float
    signals_used: int
    synthesised_at: datetime
    selection: str = ""         # "1X" | "12" | "X2" — populated when recommendation == "back"
    skip_reason: str | None = None
