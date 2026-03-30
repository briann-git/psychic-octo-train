"""Tests for PnlService."""

from unittest.mock import MagicMock

import pytest

from betting.interfaces.ledger_repository import ILedgerRepository
from betting.services.pnl_service import PnlService, PnlSummary


def _make_service(picks: list[dict]) -> PnlService:
    ledger = MagicMock(spec=ILedgerRepository)
    ledger.get_all_picks.return_value = picks
    return PnlService(ledger_repo=ledger)


def _pick(
    outcome: str | None = None,
    odds: float = 1.80,
    stake: float = 10.0,
) -> dict:
    return {
        "outcome": outcome,
        "odds": odds,
        "stake": stake,
    }


class TestZeroPicks:
    def test_zero_picks_returns_zeroed_summary(self):
        service = _make_service([])
        summary = service.compute()
        assert summary.total_picks == 0
        assert summary.settled == 0
        assert summary.pending == 0
        assert summary.won == 0
        assert summary.lost == 0
        assert summary.void == 0
        assert summary.win_rate == 0.0
        assert summary.total_staked == 0.0
        assert summary.gross_return == 0.0
        assert summary.net_pnl == 0.0
        assert summary.roi == 0.0


class TestWinRate:
    def test_win_rate_computed_correctly(self):
        picks = [
            _pick(outcome="won"),
            _pick(outcome="won"),
            _pick(outcome="lost"),
        ]
        service = _make_service(picks)
        summary = service.compute()
        assert summary.win_rate == pytest.approx(2 / 3)

    def test_win_rate_is_zero_when_no_non_void_settled(self):
        picks = [_pick(outcome="void"), _pick(outcome="void")]
        service = _make_service(picks)
        summary = service.compute()
        assert summary.win_rate == 0.0

    def test_void_picks_excluded_from_win_rate_denominator(self):
        picks = [
            _pick(outcome="won"),
            _pick(outcome="void"),
            _pick(outcome="lost"),
        ]
        service = _make_service(picks)
        summary = service.compute()
        # void is excluded — denominator is won + lost = 2
        assert summary.win_rate == pytest.approx(0.5)

    def test_pending_picks_excluded_from_win_rate(self):
        picks = [
            _pick(outcome="won"),
            _pick(outcome=None),  # pending
        ]
        service = _make_service(picks)
        summary = service.compute()
        # only 1 settled (won), 0 lost -> win_rate = 1.0
        assert summary.win_rate == pytest.approx(1.0)


class TestRoi:
    def test_roi_computed_correctly(self):
        # won: odds=2.0, stake=10 -> gross_return=20, total_staked=20 (won+lost), net=0
        picks = [
            _pick(outcome="won", odds=2.0, stake=10.0),
            _pick(outcome="lost", odds=2.0, stake=10.0),
        ]
        service = _make_service(picks)
        summary = service.compute()
        assert summary.total_staked == pytest.approx(20.0)
        assert summary.gross_return == pytest.approx(20.0)
        assert summary.net_pnl == pytest.approx(0.0)
        assert summary.roi == pytest.approx(0.0)

    def test_roi_positive_when_all_won(self):
        picks = [_pick(outcome="won", odds=2.0, stake=10.0)]
        service = _make_service(picks)
        summary = service.compute()
        assert summary.gross_return == pytest.approx(20.0)
        assert summary.net_pnl == pytest.approx(10.0)
        assert summary.roi == pytest.approx(1.0)

    def test_roi_negative_when_all_lost(self):
        picks = [_pick(outcome="lost", stake=10.0)]
        service = _make_service(picks)
        summary = service.compute()
        assert summary.gross_return == pytest.approx(0.0)
        assert summary.net_pnl == pytest.approx(-10.0)
        assert summary.roi == pytest.approx(-1.0)

    def test_roi_zero_when_no_staked_bets(self):
        # Only void picks — no stake counted
        picks = [_pick(outcome="void")]
        service = _make_service(picks)
        summary = service.compute()
        assert summary.roi == 0.0

    def test_pending_picks_excluded_from_roi(self):
        picks = [
            _pick(outcome="won", odds=2.0, stake=10.0),
            _pick(outcome=None, odds=1.50, stake=10.0),  # pending — not counted
        ]
        service = _make_service(picks)
        summary = service.compute()
        # Only the won pick affects staked
        assert summary.total_staked == pytest.approx(10.0)
        assert summary.pending == 1


class TestCounts:
    def test_total_picks_includes_pending(self):
        picks = [
            _pick(outcome="won"),
            _pick(outcome=None),
            _pick(outcome="lost"),
        ]
        service = _make_service(picks)
        summary = service.compute()
        assert summary.total_picks == 3
        assert summary.settled == 2
        assert summary.pending == 1

    def test_void_counted_in_settled_not_win_or_loss(self):
        picks = [_pick(outcome="void")]
        service = _make_service(picks)
        summary = service.compute()
        assert summary.settled == 1
        assert summary.void == 1
        assert summary.won == 0
        assert summary.lost == 0
