from datetime import datetime, timezone

from scipy.stats import poisson  # type: ignore[import-untyped]

from betting.interfaces.stats_provider import IStatsProvider
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot
from betting.models.signal import Signal

_MAX_GOALS = 7


class StatisticalService:
    def __init__(self, stats_provider: IStatsProvider) -> None:
        self._stats_provider = stats_provider

    def analyse(self, fixture: Fixture, odds: OddsSnapshot) -> Signal:
        """
        1. Fetch attack/defence ratings for both teams from stats_provider.
        2. Compute expected goals (home_xg, away_xg) via Poisson model.
        3. Build score matrix (0..7 x 0..7).
        4. Derive P(home win), P(draw), P(away win).
        5. Derive double chance probabilities (1X, 12, X2).
        6. Compare model probability to implied probability from odds.
        7. Return Signal with best selection, confidence and edge.
        """
        home_attack, home_defence, away_attack, away_defence = (
            self._stats_provider.get_attack_defence_ratings(fixture)
        )
        league_avg_home, league_avg_away = self._stats_provider.get_league_averages(
            fixture.league, fixture.season
        )

        home_xg, away_xg = self._expected_goals(
            home_attack, home_defence, away_attack, away_defence,
            league_avg_home, league_avg_away,
        )

        matrix = self._score_matrix(home_xg, away_xg)

        p_home = sum(prob for (h, a), prob in matrix.items() if h > a)
        p_draw = sum(prob for (h, a), prob in matrix.items() if h == a)
        p_away = sum(prob for (h, a), prob in matrix.items() if h < a)

        model_probs = {
            "1X": p_home + p_draw,
            "12": p_home + p_away,
            "X2": p_draw + p_away,
        }
        implied_probs = {
            "1X": 1.0 / odds.home_draw if odds.home_draw > 0 else 0.0,
            "12": 1.0 / odds.home_away if odds.home_away > 0 else 0.0,
            "X2": 1.0 / odds.draw_away if odds.draw_away > 0 else 0.0,
        }
        edges = {
            sel: model_probs[sel] - implied_probs[sel]
            for sel in ("1X", "12", "X2")
        }

        best_selection = max(edges, key=lambda s: edges[s])
        best_edge = edges[best_selection]
        best_model_prob = model_probs[best_selection]

        if best_edge > 0:
            recommendation: str = "back"
        else:
            recommendation = "skip"

        reasoning = (
            f"home_xg={home_xg:.3f}, away_xg={away_xg:.3f}; "
            f"P(1X)={model_probs['1X']:.3f}, P(12)={model_probs['12']:.3f}, "
            f"P(X2)={model_probs['X2']:.3f}; "
            f"best={best_selection} edge={best_edge:.4f}"
        )

        return Signal(
            agent_id="statistical",
            fixture_id=fixture.id,
            recommendation=recommendation,  # type: ignore[arg-type]
            confidence=best_model_prob,
            edge=best_edge,
            reasoning=reasoning,
            data_timestamp=datetime.now(tz=timezone.utc),
            selection=best_selection,
        )

    @staticmethod
    def _expected_goals(
        home_attack: float,
        home_defence: float,
        away_attack: float,
        away_defence: float,
        league_avg_home: float,
        league_avg_away: float,
    ) -> tuple[float, float]:
        home_xg = home_attack * away_defence * league_avg_home
        away_xg = away_attack * home_defence * league_avg_away
        return home_xg, away_xg

    @staticmethod
    def _score_matrix(
        home_xg: float,
        away_xg: float,
        max_goals: int = _MAX_GOALS,
    ) -> dict[tuple[int, int], float]:
        matrix: dict[tuple[int, int], float] = {}
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                matrix[(h, a)] = float(
                    poisson.pmf(h, home_xg) * poisson.pmf(a, away_xg)
                )
        return matrix
