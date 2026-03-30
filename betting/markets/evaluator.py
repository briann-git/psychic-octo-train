import logging

from betting.config.market_config import SelectionDefinition

logger = logging.getLogger(__name__)


class OutcomeEvaluator:
    """
    Evaluates whether a selection won, lost, or is void given a result.
    Dispatches to the appropriate strategy based on selection.evaluation_strategy.

    Result dict keys by strategy:
      ftr:   {"ftr": "H" | "D" | "A"}
      btts:  {"fthg": int, "ftag": int}
      total: {col: value for col in wins_if["columns"]}
    """

    def evaluate(
        self,
        selection: SelectionDefinition,
        result: dict,
    ) -> str:
        strategy = selection.evaluation_strategy
        if strategy == "ftr":
            return self._evaluate_ftr(selection.wins_if, result)
        elif strategy == "btts":
            return self._evaluate_btts(selection.wins_if, result)
        elif strategy == "total":
            return self._evaluate_total(selection.wins_if, result)
        logger.warning("Unknown evaluation strategy %r — voiding", strategy)
        return "void"

    def _evaluate_ftr(self, wins_if: str, result: dict) -> str:
        ftr = result.get("ftr", "")
        if not ftr:
            return "void"
        winning = frozenset(v.strip() for v in wins_if.split("|"))
        return "won" if ftr in winning else "lost"

    def _evaluate_btts(self, wins_if: str, result: dict) -> str:
        fthg = result.get("fthg")
        ftag = result.get("ftag")
        if fthg is None or ftag is None:
            return "void"
        both_scored = int(fthg) > 0 and int(ftag) > 0
        if wins_if == "btts_yes":
            return "won" if both_scored else "lost"
        elif wins_if == "btts_no":
            return "won" if not both_scored else "lost"
        return "void"

    def _evaluate_total(self, wins_if: dict, result: dict) -> str:
        """
        Generic total evaluator. Sums the specified columns and compares
        against the threshold using the specified operator.

        Works for any summable stat: goals, cards, corners, shots, etc.
        Columns and threshold are declared in the YAML wins_if dict.
        """
        columns = wins_if["columns"]
        operator = wins_if["operator"]
        threshold = float(wins_if["threshold"])

        values = [result.get(col) for col in columns]
        if any(v is None for v in values):
            logger.debug(
                "Missing result columns %s for total evaluation — voiding",
                [c for c, v in zip(columns, values) if v is None],
            )
            return "void"

        total = sum(float(v) for v in values)

        ops = {
            ">":  lambda t, th: t > th,
            ">=": lambda t, th: t >= th,
            "<":  lambda t, th: t < th,
            "<=": lambda t, th: t <= th,
            "==": lambda t, th: t == th,
        }
        fn = ops.get(operator)
        if not fn:
            logger.warning("Unknown operator %r in total evaluation — voiding", operator)
            return "void"

        return "won" if fn(total, threshold) else "lost"
