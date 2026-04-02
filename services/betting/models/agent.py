from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class BanditPolicy:
    """
    The learnable parameter vector for a single agent.
    All mutable — updated weekly by AgentRecalibrationService.
    """

    statistical_weight: float
    market_weight: float
    confidence_threshold: float
    staking_strategy: str
    kelly_fraction: float = 0.25
    learning_rate: float = 0.01
    update_count: int = 0

    def normalise_weights(self) -> None:
        """Ensures statistical_weight + market_weight = 1.0."""
        total = self.statistical_weight + self.market_weight
        if total > 0:
            self.statistical_weight /= total
            self.market_weight /= total

    def clip(self) -> None:
        """Clips parameters to valid ranges after update."""
        self.statistical_weight = max(0.10, min(0.90, self.statistical_weight))
        self.market_weight = max(0.10, min(0.90, self.market_weight))
        self.confidence_threshold = max(0.55, min(0.85, self.confidence_threshold))
        self.kelly_fraction = max(0.10, min(0.50, self.kelly_fraction))


@dataclass
class Agent:
    id: str
    policy: BanditPolicy
    bankroll: float
    starting_bankroll: float
    created_at: datetime
    last_updated_at: datetime
    total_picks: int = 0
    total_settled: int = 0
    decommissioned_at: Optional[datetime] = field(default=None)

    @property
    def is_decommissioned(self) -> bool:
        return self.decommissioned_at is not None
