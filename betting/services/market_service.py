from dataclasses import dataclass
from datetime import datetime, timezone

from betting.interfaces.ledger_repository import ILedgerRepository
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot
from betting.models.signal import Signal

SHORTENING_THRESHOLD = -0.05   # odds dropped by more than 0.05
DRIFTING_THRESHOLD   =  0.05   # odds rose by more than 0.05
SHARP_THRESHOLD      = -0.10   # significant shortening = sharp money signal


@dataclass
class MovementSummary:
    selection: str              # "1X" | "12" | "X2"
    opening_odds: float
    current_odds: float
    delta: float                # current - opening (negative = shortened = market backing it)
    direction: str              # "shortening" | "drifting" | "stable"
    is_sharp: bool              # True if moved against public % (significant shortening)
    snapshots_available: int


class MarketService:
    def __init__(self, ledger_repo: ILedgerRepository) -> None:
        self._ledger = ledger_repo

    def analyse(self, fixture: Fixture, current_odds: OddsSnapshot) -> Signal:
        """
        1. Fetch odds history for fixture from ledger
        2. If fewer than 2 snapshots, return low-confidence skip signal
        3. Compute line movement across all snapshots
        4. Compute CLV against pre_analysis snapshot
        5. Determine best selection and edge
        6. Return Signal
        """
        history = self._ledger.get_odds_history(fixture.id)

        # Find the best selection from current odds (largest gap between selections)
        selection = self._best_selection(current_odds)

        if len(history) < 2:
            return Signal(
                agent_id="market",
                fixture_id=fixture.id,
                recommendation="skip",
                confidence=0.0,
                edge=0.0,
                reasoning="insufficient odds history",
                data_timestamp=datetime.now(tz=timezone.utc),
                selection=selection,
            )

        opening_row = history[0]
        movement = self._compute_movement(selection, opening_row, current_odds, len(history))
        return self._build_signal(fixture, movement)

    def _best_selection(self, odds: OddsSnapshot) -> str:
        """Pick the selection with the best (highest) implied probability."""
        implied = {
            "1X": 1.0 / odds.home_draw if odds.home_draw > 0 else 0.0,
            "12": 1.0 / odds.home_away if odds.home_away > 0 else 0.0,
            "X2": 1.0 / odds.draw_away if odds.draw_away > 0 else 0.0,
        }
        return max(implied, key=lambda s: implied[s])

    def _compute_movement(
        self,
        selection: str,
        opening_row: dict,
        current_odds: OddsSnapshot,
        snapshots_available: int,
    ) -> MovementSummary:
        col_map = {"1X": "home_draw", "12": "home_away", "X2": "draw_away"}
        col = col_map[selection]

        opening_odds = float(opening_row[col])
        current = getattr(current_odds, col)
        delta = current - opening_odds

        if delta < SHARP_THRESHOLD:
            direction = "shortening"
            is_sharp = True
        elif delta < SHORTENING_THRESHOLD:
            direction = "shortening"
            is_sharp = False
        elif delta > DRIFTING_THRESHOLD:
            direction = "drifting"
            is_sharp = False
        else:
            direction = "stable"
            is_sharp = False

        return MovementSummary(
            selection=selection,
            opening_odds=opening_odds,
            current_odds=current,
            delta=delta,
            direction=direction,
            is_sharp=is_sharp,
            snapshots_available=snapshots_available,
        )

    def _clv(
        self,
        model_implied_prob: float,
        pre_analysis_odds: float,
    ) -> float:
        """
        CLV = model_implied_prob - (1 / pre_analysis_odds)
        Positive = you have edge over where market closed.
        Reserved for future use when pre_analysis snapshot-based CLV is integrated.
        """
        if pre_analysis_odds <= 0:
            return 0.0
        return model_implied_prob - (1.0 / pre_analysis_odds)

    def _build_signal(
        self,
        fixture: Fixture,
        movement: MovementSummary,
    ) -> Signal:
        if movement.snapshots_available < 2:
            return Signal(
                agent_id="market",
                fixture_id=fixture.id,
                recommendation="skip",
                confidence=0.0,
                edge=0.0,
                reasoning="insufficient odds history",
                data_timestamp=datetime.now(tz=timezone.utc),
                selection=movement.selection,
            )

        if movement.is_sharp:
            confidence = 0.75
            edge = abs(movement.delta) / movement.opening_odds
            recommendation = "back"
        elif movement.direction == "shortening":
            confidence = 0.55
            edge = abs(movement.delta) / movement.opening_odds
            recommendation = "back"
        elif movement.direction == "drifting":
            confidence = 0.30
            edge = -abs(movement.delta) / movement.opening_odds
            recommendation = "skip"
        else:
            confidence = 0.50
            edge = 0.0
            recommendation = "skip"

        reasoning = (
            f"opening={movement.opening_odds:.3f}, current={movement.current_odds:.3f}, "
            f"delta={movement.delta:.3f}, direction={movement.direction}, "
            f"sharp={movement.is_sharp}, snapshots={movement.snapshots_available}"
        )

        return Signal(
            agent_id="market",
            fixture_id=fixture.id,
            recommendation=recommendation,  # type: ignore[arg-type]
            confidence=confidence,
            edge=edge,
            reasoning=reasoning,
            data_timestamp=datetime.now(tz=timezone.utc),
            selection=movement.selection,
        )
