"""Tests for ProbabilityCalculator implementations."""

import logging
import pytest

from betting.config.market_config import SelectionDefinition
from betting.markets.probability import (
    BttsProbabilityCalculator,
    FtrProbabilityCalculator,
    TotalProbabilityCalculator,
    get_calculator,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sel(wins_if, strategy="ftr") -> SelectionDefinition:
    return SelectionDefinition(
        id="test",
        label="Test",
        wins_if=wins_if,
        evaluation_strategy=strategy,
    )


def _simple_matrix() -> dict[tuple[int, int], float]:
    """
    A small deterministic matrix:
      (0,0)=0.10  (0,1)=0.05  (0,2)=0.02
      (1,0)=0.15  (1,1)=0.10  (1,2)=0.05
      (2,0)=0.20  (2,1)=0.15  (2,2)=0.08
      (3,0)=0.05  (3,1)=0.03  (3,2)=0.02
    Total = 1.00

    FTR breakdown:
      H (h > a): (1,0)=0.15, (2,0)=0.20, (2,1)=0.15, (3,0)=0.05, (3,1)=0.03, (3,2) — h=3>a=2
               = 0.15 + 0.20 + 0.15 + 0.05 + 0.03 + 0.02 = 0.60
      D (h == a): (0,0)=0.10, (1,1)=0.10, (2,2)=0.08 = 0.28
      A (h < a): (0,1)=0.05, (0,2)=0.02, (1,2)=0.05 = 0.12
    """
    return {
        (0, 0): 0.10, (0, 1): 0.05, (0, 2): 0.02,
        (1, 0): 0.15, (1, 1): 0.10, (1, 2): 0.05,
        (2, 0): 0.20, (2, 1): 0.15, (2, 2): 0.08,
        (3, 0): 0.05, (3, 1): 0.03, (3, 2): 0.02,
    }


# ---------------------------------------------------------------------------
# FtrProbabilityCalculator
# ---------------------------------------------------------------------------

class TestFtrProbabilityCalculator:
    calc = FtrProbabilityCalculator()

    def test_1X_home_or_draw(self):
        matrix = _simple_matrix()
        # H=0.60, D=0.28 → 1X = 0.88
        result = self.calc.calculate(_sel("H | D"), matrix, 1.5, 1.2)
        assert result == pytest.approx(0.88)

    def test_12_home_or_away(self):
        matrix = _simple_matrix()
        # H=0.60, A=0.12 → 12 = 0.72
        result = self.calc.calculate(_sel("H | A"), matrix, 1.5, 1.2)
        assert result == pytest.approx(0.72)

    def test_X2_draw_or_away(self):
        matrix = _simple_matrix()
        # D=0.28, A=0.12 → X2 = 0.40
        result = self.calc.calculate(_sel("D | A"), matrix, 1.5, 1.2)
        assert result == pytest.approx(0.40)

    def test_single_H_equals_home_win_cells(self):
        matrix = _simple_matrix()
        expected = sum(p for (h, a), p in matrix.items() if h > a)
        result = self.calc.calculate(_sel("H"), matrix, 1.5, 1.2)
        assert result == pytest.approx(expected)

    def test_non_string_wins_if_returns_zero(self):
        matrix = _simple_matrix()
        result = self.calc.calculate(_sel({"columns": ["fthg", "ftag"]}), matrix, 1.5, 1.2)
        assert result == 0.0

    def test_unknown_ftr_code_ignored_gracefully(self):
        matrix = _simple_matrix()
        # "Z" is unknown — should be silently ignored; only "H" contributes
        expected = sum(p for (h, a), p in matrix.items() if h > a)
        result = self.calc.calculate(_sel("H | Z"), matrix, 1.5, 1.2)
        assert result == pytest.approx(expected)


# ---------------------------------------------------------------------------
# BttsProbabilityCalculator
# ---------------------------------------------------------------------------

class TestBttsProbabilityCalculator:
    calc = BttsProbabilityCalculator()

    def test_btts_yes_probability(self):
        matrix = _simple_matrix()
        # Cells with h > 0 and a > 0: (1,1)=0.10, (1,2)=0.05, (2,1)=0.15, (2,2)=0.08,
        #                              (3,1)=0.03, (3,2)=0.02 = 0.43
        expected = sum(p for (h, a), p in matrix.items() if h > 0 and a > 0)
        result = self.calc.calculate(_sel("btts_yes", "btts"), matrix, 1.5, 1.2)
        assert result == pytest.approx(expected)

    def test_btts_no_probability(self):
        matrix = _simple_matrix()
        expected = sum(p for (h, a), p in matrix.items() if h == 0 or a == 0)
        result = self.calc.calculate(_sel("btts_no", "btts"), matrix, 1.5, 1.2)
        assert result == pytest.approx(expected)

    def test_yes_plus_no_sums_to_one(self):
        matrix = _simple_matrix()
        yes = self.calc.calculate(_sel("btts_yes", "btts"), matrix, 1.5, 1.2)
        no = self.calc.calculate(_sel("btts_no", "btts"), matrix, 1.5, 1.2)
        assert yes + no == pytest.approx(1.0, abs=1e-9)

    def test_unknown_wins_if_returns_zero(self):
        matrix = _simple_matrix()
        result = self.calc.calculate(_sel("btts_maybe", "btts"), matrix, 1.5, 1.2)
        assert result == 0.0


# ---------------------------------------------------------------------------
# TotalProbabilityCalculator
# ---------------------------------------------------------------------------

class TestTotalProbabilityCalculator:
    calc = TotalProbabilityCalculator()

    def _over_sel(self, threshold: float) -> SelectionDefinition:
        return _sel({"columns": ["fthg", "ftag"], "operator": ">", "threshold": threshold}, "total")

    def _under_sel(self, threshold: float) -> SelectionDefinition:
        return _sel({"columns": ["fthg", "ftag"], "operator": "<=", "threshold": threshold}, "total")

    def test_over_25_probability(self):
        matrix = _simple_matrix()
        expected = sum(p for (h, a), p in matrix.items() if h + a > 2.5)
        result = self.calc.calculate(self._over_sel(2.5), matrix, 1.5, 1.2)
        assert result == pytest.approx(expected)

    def test_under_25_probability(self):
        matrix = _simple_matrix()
        expected = sum(p for (h, a), p in matrix.items() if h + a <= 2.5)
        result = self.calc.calculate(self._under_sel(2.5), matrix, 1.5, 1.2)
        assert result == pytest.approx(expected)

    def test_over_plus_under_sums_to_one(self):
        matrix = _simple_matrix()
        over = self.calc.calculate(self._over_sel(2.5), matrix, 1.5, 1.2)
        under = self.calc.calculate(self._under_sel(2.5), matrix, 1.5, 1.2)
        assert over + under == pytest.approx(1.0, abs=1e-9)

    def test_non_goal_columns_logs_warning_and_returns_zero(self, caplog):
        matrix = _simple_matrix()
        sel = _sel({"columns": ["hy", "ay", "hr", "ar"], "operator": ">", "threshold": 3.5}, "total")
        with caplog.at_level(logging.WARNING, logger="betting.markets.probability"):
            result = self.calc.calculate(sel, matrix, 1.5, 1.2)
        assert result == 0.0
        assert "TotalProbabilityCalculator only supports goal columns" in caplog.text

    def test_unknown_operator_logs_warning_and_returns_zero(self, caplog):
        matrix = _simple_matrix()
        sel = _sel({"columns": ["fthg", "ftag"], "operator": "!=", "threshold": 2.5}, "total")
        with caplog.at_level(logging.WARNING, logger="betting.markets.probability"):
            result = self.calc.calculate(sel, matrix, 1.5, 1.2)
        assert result == 0.0
        assert "Unknown operator" in caplog.text

    def test_non_dict_wins_if_returns_zero(self):
        matrix = _simple_matrix()
        result = self.calc.calculate(_sel("H | D", "total"), matrix, 1.5, 1.2)
        assert result == 0.0


# ---------------------------------------------------------------------------
# get_calculator registry
# ---------------------------------------------------------------------------

class TestGetCalculator:
    def test_returns_ftr_calculator(self):
        calc = get_calculator("ftr")
        assert isinstance(calc, FtrProbabilityCalculator)

    def test_returns_btts_calculator(self):
        calc = get_calculator("btts")
        assert isinstance(calc, BttsProbabilityCalculator)

    def test_returns_total_calculator(self):
        calc = get_calculator("total")
        assert isinstance(calc, TotalProbabilityCalculator)

    def test_returns_none_for_unknown_strategy(self, caplog):
        with caplog.at_level(logging.WARNING, logger="betting.markets.probability"):
            calc = get_calculator("unknown_strategy")
        assert calc is None
        assert "No probability calculator registered for strategy" in caplog.text
