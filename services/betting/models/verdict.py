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

    @classmethod
    def from_dict(cls, data: dict) -> "Verdict":
        d = dict(data)
        if isinstance(d.get("synthesised_at"), str):
            d["synthesised_at"] = datetime.fromisoformat(d["synthesised_at"])
        return cls(**d)
