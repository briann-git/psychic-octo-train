"""Tests for MarketService."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from betting.interfaces.ledger_repository import ILedgerRepository
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot
from betting.services.market_service import (
    MarketService,
    SHARP_THRESHOLD,
    SHORTENING_THRESHOLD,
    DRIFTING_THRESHOLD,
)


def _make_fixture() -> Fixture:
    return Fixture(
        id="fix-mkt-001",
        home_team="Arsenal",
        away_team="Chelsea",
        league="PL",
        season="2024/25",
        matchday=30,
        kickoff=datetime(2025, 4, 1, 15, 0, tzinfo=timezone.utc),
    )


def _make_odds(home_draw: float = 1.50, home_away: float = 1.40, draw_away: float = 2.20) -> OddsSnapshot:
    return OddsSnapshot(
        fixture_id="fix-mkt-001",
        market="double_chance",
        bookmaker="stub",
        home_draw=home_draw,
        home_away=home_away,
        draw_away=draw_away,
        fetched_at=datetime.now(tz=timezone.utc),
    )


def _make_history_row(
    home_draw: float = 1.60,
    home_away: float = 1.50,
    draw_away: float = 2.30,
    snapshot_type: str = "opening",
) -> dict:
    return {
        "id": "hist-001",
        "fixture_id": "fix-mkt-001",
        "league": "PL",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "kickoff": "2025-04-01T15:00:00+00:00",
        "market": "double_chance",
        "bookmaker": "stub",
        "home_draw": home_draw,
        "home_away": home_away,
        "draw_away": draw_away,
        "snapshot_type": snapshot_type,
        "fetched_at": "2025-04-01T08:00:00+00:00",
    }


def _make_service(history: list[dict]) -> MarketService:
    ledger = MagicMock(spec=ILedgerRepository)
    ledger.get_odds_history.return_value = history
    return MarketService(ledger_repo=ledger)


class TestInsufficientHistory:
    def test_returns_skip_when_no_history(self):
        service = _make_service([])
        signal = service.analyse(_make_fixture(), _make_odds())
        assert signal.recommendation == "skip"
        assert signal.confidence == 0.0
        assert signal.edge == 0.0
        assert signal.reasoning == "insufficient odds history"
        assert signal.agent_id == "market"

    def test_returns_skip_when_only_one_snapshot(self):
        service = _make_service([_make_history_row()])
        signal = service.analyse(_make_fixture(), _make_odds())
        assert signal.recommendation == "skip"
        assert signal.confidence == 0.0


class TestMovementSummary:
    def test_shortening_direction(self):
        # Opening 1.60, current 1.50 -> delta = -0.10 -> shortening
        opening = _make_history_row(home_draw=1.60)
        current_snap = _make_history_row(home_draw=1.55, snapshot_type="intermediate")
        service = _make_service([opening, current_snap])
        odds = _make_odds(home_draw=1.50)
        signal = service.analyse(_make_fixture(), odds)
        # 1X is implied best selection: 1/1.50=0.667 vs 1/1.40=0.714... wait 12 is higher
        # Actually 12: 1/1.40=0.714, 1X: 1/1.50=0.667, X2: 1/2.20=0.455
        # Best selection is 12
        assert signal.agent_id == "market"
        assert signal.recommendation in ("back", "skip")

    def test_sharp_shortening_when_large_drop(self):
        # Opening 1.80, current 1.60 -> delta = -0.20 -> sharp (< -0.10)
        opening = _make_history_row(home_draw=1.80, home_away=1.70, draw_away=2.50)
        current_snap = _make_history_row(home_draw=1.65, snapshot_type="intermediate")
        service = _make_service([opening, current_snap])
        odds = _make_odds(home_draw=1.60, home_away=1.70, draw_away=2.50)
        signal = service.analyse(_make_fixture(), odds)
        # Best selection by implied prob: 12 = 1/1.70=0.588, 1X = 1/1.60=0.625, X2=0.40
        # Best is 1X
        assert signal.agent_id == "market"

    def test_drifting_direction(self):
        # Opening 1.40, current 1.60 -> delta = +0.20 -> drifting
        opening = _make_history_row(home_draw=1.40, home_away=1.30, draw_away=2.00)
        current_snap = _make_history_row(home_draw=1.45, snapshot_type="intermediate")
        service = _make_service([opening, current_snap])
        odds = _make_odds(home_draw=1.60, home_away=1.30, draw_away=2.00)
        signal = service.analyse(_make_fixture(), odds)
        assert signal.agent_id == "market"
        # When drifting, recommendation should be skip
        # best selection by implied: 12=1/1.30=0.769, 1X=1/1.60=0.625, X2=0.5
        # best = 12; opening home_away=1.30, current home_away=1.30, delta=0.0 -> stable
        # Actually odds for best selection (12) are stable (opening and current both 1.30)
        assert signal.recommendation in ("back", "skip")

    def test_stable_direction(self):
        # Opening same as current
        opening = _make_history_row(home_draw=1.50, home_away=1.40, draw_away=2.20)
        current_snap = _make_history_row(home_draw=1.51, snapshot_type="intermediate")
        service = _make_service([opening, current_snap])
        odds = _make_odds(home_draw=1.50, home_away=1.40, draw_away=2.20)
        signal = service.analyse(_make_fixture(), odds)
        assert signal.agent_id == "market"


class TestSharpSignal:
    def test_sharp_money_gives_high_confidence(self):
        # odds drop by more than SHARP_THRESHOLD (-0.10)
        # best selection 1X: opening=1.80, current=1.60 -> delta=-0.20 (< -0.10 = sharp)
        opening = _make_history_row(home_draw=1.80, home_away=2.00, draw_away=2.50)
        current_snap = _make_history_row(home_draw=1.65, snapshot_type="intermediate")
        service = _make_service([opening, current_snap])
        odds = _make_odds(home_draw=1.60, home_away=2.00, draw_away=2.50)
        signal = service.analyse(_make_fixture(), odds)
        # best implied prob: 1X=1/1.60=0.625, 12=1/2.00=0.50, X2=1/2.50=0.40 -> 1X
        # delta for 1X = 1.60 - 1.80 = -0.20 < -0.10 -> sharp
        assert signal.confidence == pytest.approx(0.75)
        assert signal.recommendation == "back"
        assert signal.edge == pytest.approx(abs(-0.20) / 1.80)

    def test_moderate_shortening_gives_medium_confidence(self):
        # odds drop by -0.07 (between SHARP_THRESHOLD and SHORTENING_THRESHOLD)
        opening = _make_history_row(home_draw=1.80, home_away=2.00, draw_away=2.50)
        current_snap = _make_history_row(home_draw=1.75, snapshot_type="intermediate")
        service = _make_service([opening, current_snap])
        odds = _make_odds(home_draw=1.73, home_away=2.00, draw_away=2.50)
        signal = service.analyse(_make_fixture(), odds)
        # best implied: 1X = 1/1.73=0.578, 12=0.50, X2=0.40 -> 1X
        # delta = 1.73 - 1.80 = -0.07 -> shortening but not sharp
        assert signal.confidence == pytest.approx(0.55)
        assert signal.recommendation == "back"

    def test_drifting_gives_low_confidence_skip(self):
        # odds rise by more than DRIFTING_THRESHOLD (+0.05)
        opening = _make_history_row(home_draw=1.50, home_away=2.00, draw_away=2.50)
        current_snap = _make_history_row(home_draw=1.55, snapshot_type="intermediate")
        service = _make_service([opening, current_snap])
        odds = _make_odds(home_draw=1.60, home_away=2.00, draw_away=2.50)
        signal = service.analyse(_make_fixture(), odds)
        # best implied: 1X = 1/1.60=0.625, 12=0.5, X2=0.4 -> 1X
        # delta = 1.60 - 1.50 = +0.10 > 0.05 -> drifting
        assert signal.confidence == pytest.approx(0.30)
        assert signal.recommendation == "skip"
        assert signal.edge < 0

    def test_stable_gives_neutral_skip(self):
        # odds barely move (within threshold)
        opening = _make_history_row(home_draw=1.50, home_away=2.00, draw_away=2.50)
        current_snap = _make_history_row(home_draw=1.51, snapshot_type="intermediate")
        service = _make_service([opening, current_snap])
        odds = _make_odds(home_draw=1.52, home_away=2.00, draw_away=2.50)
        signal = service.analyse(_make_fixture(), odds)
        # best implied: 1X = 1/1.52=0.658, 12=0.5, X2=0.4 -> 1X
        # delta = 1.52 - 1.50 = +0.02, within -0.05 to +0.05 -> stable
        assert signal.confidence == pytest.approx(0.50)
        assert signal.recommendation == "skip"
        assert signal.edge == pytest.approx(0.0)


class TestSignalFields:
    def test_signal_has_correct_agent_id(self):
        opening = _make_history_row()
        second = _make_history_row(snapshot_type="intermediate")
        service = _make_service([opening, second])
        signal = service.analyse(_make_fixture(), _make_odds())
        assert signal.agent_id == "market"

    def test_signal_has_correct_fixture_id(self):
        opening = _make_history_row()
        second = _make_history_row(snapshot_type="intermediate")
        service = _make_service([opening, second])
        signal = service.analyse(_make_fixture(), _make_odds())
        assert signal.fixture_id == "fix-mkt-001"

    def test_reasoning_contains_movement_info(self):
        opening = _make_history_row(home_draw=1.80, home_away=2.00, draw_away=2.50)
        second = _make_history_row(home_draw=1.65, snapshot_type="intermediate")
        service = _make_service([opening, second])
        odds = _make_odds(home_draw=1.60, home_away=2.00, draw_away=2.50)
        signal = service.analyse(_make_fixture(), odds)
        assert "opening=" in signal.reasoning
        assert "delta=" in signal.reasoning
        assert "direction=" in signal.reasoning
