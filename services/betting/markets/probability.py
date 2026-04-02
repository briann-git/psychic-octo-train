import logging
from abc import ABC, abstractmethod
from typing import Callable

from betting.config.market_config import SelectionDefinition

logger = logging.getLogger(__name__)


class ProbabilityCalculator(ABC):
    @abstractmethod
    def calculate(
        self,
        selection: SelectionDefinition,
        matrix: dict[tuple[int, int], float],
        home_xg: float,
        away_xg: float,
    ) -> float:
        """
        Returns model probability for this selection given the Poisson score matrix.

        Args:
            selection:  SelectionDefinition from the market registry
            matrix:     score matrix — keys are (home_goals, away_goals),
                        values are P(home=h, away=a) from Poisson model
            home_xg:    expected home goals (used by some calculators)
            away_xg:    expected away goals (used by some calculators)

        Returns:
            float in [0.0, 1.0]
        """
        ...


class FtrProbabilityCalculator(ProbabilityCalculator):
    """
    Computes probability for FTR-based selections (home win, draw, away win,
    and combinations thereof — double chance).

    Maps FTR codes to matrix conditions:
      "H" — home goals > away goals
      "D" — home goals == away goals
      "A" — home goals < away goals

    A selection with wins_if "H | D" sums P(home win) + P(draw).
    Works for any market whose selections are combinations of H, D, A.
    """

    _FTR_CONDITIONS: dict[str, Callable[[int, int], bool]] = {
        "H": lambda h, a: h > a,
        "D": lambda h, a: h == a,
        "A": lambda h, a: h < a,
    }

    def calculate(
        self,
        selection: SelectionDefinition,
        matrix: dict[tuple[int, int], float],
        home_xg: float,
        away_xg: float,
    ) -> float:
        if not isinstance(selection.wins_if, str):
            return 0.0
        codes = frozenset(v.strip() for v in selection.wins_if.split("|"))
        return sum(
            prob
            for (h, a), prob in matrix.items()
            if any(
                self._FTR_CONDITIONS[code](h, a)
                for code in codes
                if code in self._FTR_CONDITIONS
            )
        )


class BttsProbabilityCalculator(ProbabilityCalculator):
    """
    Computes probability for BTTS selections.

    btts_yes: P(home > 0 AND away > 0)
    btts_no:  P(home == 0 OR away == 0)
    """

    def calculate(
        self,
        selection: SelectionDefinition,
        matrix: dict[tuple[int, int], float],
        home_xg: float,
        away_xg: float,
    ) -> float:
        if selection.wins_if == "btts_yes":
            return sum(
                prob for (h, a), prob in matrix.items()
                if h > 0 and a > 0
            )
        elif selection.wins_if == "btts_no":
            return sum(
                prob for (h, a), prob in matrix.items()
                if h == 0 or a == 0
            )
        return 0.0


class TotalProbabilityCalculator(ProbabilityCalculator):
    """
    Computes probability for total-based selections (over/under goals).

    Uses the wins_if dict to determine which matrix cells satisfy the condition.
    Currently supports goal totals (fthg + ftag) — the matrix directly encodes
    these as (h, a) cell coordinates.

    For non-goal totals (cards, corners) the matrix cannot be used directly
    as these stats are not modelled by the Poisson goal model. Returns 0.0
    with a warning for unsupported column sets.

    Supported columns: ["fthg", "ftag"] (goal total from Poisson matrix)
    """

    _GOAL_COLUMNS = frozenset(["fthg", "ftag"])

    _OPS: dict[str, Callable[[float, float], bool]] = {
        ">":  lambda t, th: t > th,
        ">=": lambda t, th: t >= th,
        "<":  lambda t, th: t < th,
        "<=": lambda t, th: t <= th,
        "==": lambda t, th: t == th,
    }

    def calculate(
        self,
        selection: SelectionDefinition,
        matrix: dict[tuple[int, int], float],
        home_xg: float,
        away_xg: float,
    ) -> float:
        if not isinstance(selection.wins_if, dict):
            return 0.0

        columns = frozenset(selection.wins_if.get("columns", []))
        operator = selection.wins_if.get("operator", "")
        threshold = float(selection.wins_if.get("threshold", 0))

        if columns != self._GOAL_COLUMNS:
            logger.warning(
                "TotalProbabilityCalculator only supports goal columns %s "
                "— got %s. Returning 0.0. Use a dedicated calculator for "
                "non-goal totals.",
                self._GOAL_COLUMNS, columns,
            )
            return 0.0

        fn = self._OPS.get(operator)
        if not fn:
            logger.warning("Unknown operator %r — returning 0.0", operator)
            return 0.0

        return sum(
            prob for (h, a), prob in matrix.items()
            if fn(h + a, threshold)
        )


# TODO: register card/corner calculators when those markets go active
_CALCULATORS: dict[str, ProbabilityCalculator] = {
    "ftr":   FtrProbabilityCalculator(),
    "btts":  BttsProbabilityCalculator(),
    "total": TotalProbabilityCalculator(),
}


def get_calculator(evaluation_strategy: str) -> ProbabilityCalculator | None:
    """Returns the calculator for the given strategy, or None if unsupported."""
    calc = _CALCULATORS.get(evaluation_strategy)
    if not calc:
        logger.warning(
            "No probability calculator registered for strategy %r",
            evaluation_strategy,
        )
    return calc
