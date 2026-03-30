"""Tests for OutcomeEvaluator."""

import pytest

from betting.config.market_config import SelectionDefinition
from betting.markets.evaluator import OutcomeEvaluator


def _sel(wins_if, strategy="ftr") -> SelectionDefinition:
    return SelectionDefinition(
        id="test",
        label="Test Selection",
        wins_if=wins_if,
        evaluation_strategy=strategy,
    )


@pytest.fixture()
def evaluator() -> OutcomeEvaluator:
    return OutcomeEvaluator()


class TestFtrStrategy:
    def test_1x_wins_on_home(self, evaluator):
        assert evaluator.evaluate(_sel("H | D"), {"ftr": "H"}) == "won"

    def test_1x_wins_on_draw(self, evaluator):
        assert evaluator.evaluate(_sel("H | D"), {"ftr": "D"}) == "won"

    def test_1x_loses_on_away(self, evaluator):
        assert evaluator.evaluate(_sel("H | D"), {"ftr": "A"}) == "lost"

    def test_12_wins_on_home(self, evaluator):
        assert evaluator.evaluate(_sel("H | A"), {"ftr": "H"}) == "won"

    def test_12_wins_on_away(self, evaluator):
        assert evaluator.evaluate(_sel("H | A"), {"ftr": "A"}) == "won"

    def test_12_loses_on_draw(self, evaluator):
        assert evaluator.evaluate(_sel("H | A"), {"ftr": "D"}) == "lost"

    def test_x2_wins_on_draw(self, evaluator):
        assert evaluator.evaluate(_sel("D | A"), {"ftr": "D"}) == "won"

    def test_x2_wins_on_away(self, evaluator):
        assert evaluator.evaluate(_sel("D | A"), {"ftr": "A"}) == "won"

    def test_x2_loses_on_home(self, evaluator):
        assert evaluator.evaluate(_sel("D | A"), {"ftr": "H"}) == "lost"

    def test_empty_ftr_returns_void(self, evaluator):
        assert evaluator.evaluate(_sel("H | D"), {"ftr": ""}) == "void"

    def test_missing_ftr_returns_void(self, evaluator):
        assert evaluator.evaluate(_sel("H | D"), {}) == "void"


class TestBttsStrategy:
    def test_btts_yes_wins_when_both_scored(self, evaluator):
        result = {"fthg": 1, "ftag": 2}
        assert evaluator.evaluate(_sel("btts_yes", "btts"), result) == "won"

    def test_btts_yes_loses_when_one_team_zero(self, evaluator):
        result = {"fthg": 0, "ftag": 2}
        assert evaluator.evaluate(_sel("btts_yes", "btts"), result) == "lost"

    def test_btts_no_wins_when_one_team_zero(self, evaluator):
        result = {"fthg": 0, "ftag": 2}
        assert evaluator.evaluate(_sel("btts_no", "btts"), result) == "won"

    def test_btts_no_loses_when_both_scored(self, evaluator):
        result = {"fthg": 1, "ftag": 1}
        assert evaluator.evaluate(_sel("btts_no", "btts"), result) == "lost"

    def test_btts_void_when_missing_fthg(self, evaluator):
        assert evaluator.evaluate(_sel("btts_yes", "btts"), {"ftag": 1}) == "void"

    def test_btts_void_when_missing_ftag(self, evaluator):
        assert evaluator.evaluate(_sel("btts_yes", "btts"), {"fthg": 1}) == "void"


class TestTotalStrategy:
    def test_over_25_wins(self, evaluator):
        wins_if = {"columns": ["fthg", "ftag"], "operator": ">", "threshold": 2.5}
        result = {"fthg": 2, "ftag": 1}  # total 3 > 2.5
        assert evaluator.evaluate(_sel(wins_if, "total"), result) == "won"

    def test_over_25_loses(self, evaluator):
        wins_if = {"columns": ["fthg", "ftag"], "operator": ">", "threshold": 2.5}
        result = {"fthg": 1, "ftag": 1}  # total 2 <= 2.5
        assert evaluator.evaluate(_sel(wins_if, "total"), result) == "lost"

    def test_under_25_wins(self, evaluator):
        wins_if = {"columns": ["fthg", "ftag"], "operator": "<=", "threshold": 2.5}
        result = {"fthg": 1, "ftag": 1}  # total 2 <= 2.5
        assert evaluator.evaluate(_sel(wins_if, "total"), result) == "won"

    def test_under_25_loses(self, evaluator):
        wins_if = {"columns": ["fthg", "ftag"], "operator": "<=", "threshold": 2.5}
        result = {"fthg": 2, "ftag": 1}  # total 3 > 2.5
        assert evaluator.evaluate(_sel(wins_if, "total"), result) == "lost"

    def test_cards_over_35(self, evaluator):
        wins_if = {"columns": ["hy", "ay", "hr", "ar"], "operator": ">", "threshold": 3.5}
        result = {"hy": 2, "ay": 1, "hr": 1, "ar": 0}  # total 4 > 3.5
        assert evaluator.evaluate(_sel(wins_if, "total"), result) == "won"

    def test_cards_under_35(self, evaluator):
        wins_if = {"columns": ["hy", "ay", "hr", "ar"], "operator": "<=", "threshold": 3.5}
        result = {"hy": 1, "ay": 1, "hr": 0, "ar": 0}  # total 2 <= 3.5
        assert evaluator.evaluate(_sel(wins_if, "total"), result) == "won"

    def test_total_void_when_missing_column(self, evaluator):
        wins_if = {"columns": ["fthg", "ftag"], "operator": ">", "threshold": 2.5}
        result = {"fthg": 2}  # missing ftag
        assert evaluator.evaluate(_sel(wins_if, "total"), result) == "void"

    def test_total_equal_operator(self, evaluator):
        wins_if = {"columns": ["fthg", "ftag"], "operator": "==", "threshold": 3.0}
        result = {"fthg": 2, "ftag": 1}  # total 3 == 3.0
        assert evaluator.evaluate(_sel(wins_if, "total"), result) == "won"

    def test_total_gte_operator(self, evaluator):
        wins_if = {"columns": ["fthg", "ftag"], "operator": ">=", "threshold": 2.5}
        result = {"fthg": 2, "ftag": 1}  # total 3 >= 2.5
        assert evaluator.evaluate(_sel(wins_if, "total"), result) == "won"

    def test_total_lt_operator(self, evaluator):
        wins_if = {"columns": ["fthg", "ftag"], "operator": "<", "threshold": 2.5}
        result = {"fthg": 1, "ftag": 1}  # total 2 < 2.5
        assert evaluator.evaluate(_sel(wins_if, "total"), result) == "won"


class TestUnknownStrategy:
    def test_unknown_strategy_returns_void(self, evaluator):
        sel = SelectionDefinition(
            id="test",
            label="Test",
            wins_if="something",
            evaluation_strategy="unknown_strategy",
        )
        assert evaluator.evaluate(sel, {"ftr": "H"}) == "void"

    def test_unknown_operator_returns_void(self, evaluator):
        wins_if = {"columns": ["fthg", "ftag"], "operator": "!=", "threshold": 2.5}
        result = {"fthg": 2, "ftag": 1}
        assert evaluator.evaluate(_sel(wins_if, "total"), result) == "void"
