from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class Signal:
    agent_id: str
    fixture_id: str
    recommendation: Literal["back", "lay", "skip"]
    confidence: float
    edge: float
    reasoning: str
    data_timestamp: datetime
    selection: str = ""         # "1X" | "12" | "X2" — populated by StatisticalService
    veto: bool = False
    veto_reason: str | None = None
