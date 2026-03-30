from datetime import datetime, timezone

from scipy.stats import poisson  # type: ignore[import-untyped]

from betting.config.market_config import MarketConfigLoader
from betting.interfaces.stats_provider import IStatsProvider
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot
from betting.models.signal import Signal

_MAX_GOALS = 7


class StatisticalService:
    def __init__(
        self,
        stats_provider: IStatsProvider,
        market_loader: MarketConfigLoader | None = None,
    ) -> None:
        self._stats_provider = stats_provider
        self._market_loader = market_loader or MarketConfigLoader()

    def analyse(self, fixture: Fixture, odds: OddsSnapshot) -> Signal:
        """
        1. Fetch attack/defence ratings for both teams from stats_provider.
        2. Compute expected goals (home_xg, away_xg) via Poisson model.
        3. Build score matrix (0..7 x 0..7).
        4. Derive P(home win), P(draw), P(away win).
        5. Derive selection probabilities from market registry.
        6. Compare model probability to implied probability from odds.
        7. Return Signal with best selection, confidence and edge.
        """
        market = self._market_loader.get(odds.market)
        if not market:
            raise ValueError(f"Market {odds.market!r} not in registry")

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

        # FTR code -> model probability mapping
        ftr_probs = {"H": p_home, "D": p_draw, "A": p_away}

        edges: dict[str, float] = {}
        model_probs: dict[str, float] = {}

        for sel in market.selections:
            codes = [c.strip() for c in sel.wins_if.split("|")] if isinstance(sel.wins_if, str) else []
            model_prob = sum(ftr_probs.get(code, 0.0) for code in codes)
            implied_prob = 1.0 / odds.selections[sel.id] if odds.selections.get(sel.id, 0) > 0 else 0.0
            edges[sel.id] = model_prob - implied_prob
            model_probs[sel.id] = model_prob

        best_selection = max(edges, key=lambda s: edges[s])
        best_edge = edges[best_selection]
        best_model_prob = model_probs[best_selection]

        if best_edge > 0:
            recommendation: str = "back"
        else:
            recommendation = "skip"

        reasoning = (
            f"home_xg={home_xg:.3f}, away_xg={away_xg:.3f}; "
            + "; ".join(
                f"P({sel.id})={model_probs[sel.id]:.3f}"
                for sel in market.selections
            )
            + f"; best={best_selection} edge={best_edge:.4f}"
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
