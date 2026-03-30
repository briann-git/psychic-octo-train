"""Tests for PnlService."""

from unittest.mock import MagicMock

import pytest

from betting.interfaces.ledger_repository import ILedgerRepository
from betting.services.pnl_service import PnlService, PnlSummary


def _make_service(picks: list[dict], skips: list[dict] | None = None) -> PnlService:
    ledger = MagicMock(spec=ILedgerRepository)
    ledger.get_all_picks.return_value = picks
    ledger.get_all_skips.return_value = skips if skips is not None else []
    return PnlService(ledger_repo=ledger)


def _pick(
    outcome: str | None = None,
    odds: float = 1.80,
    stake: float = 10.0,
    confidence: float = 0.65,
    opening_odds: float | None = None,
    selection_odds: float | None = None,
) -> dict:
    d: dict = {
        "outcome": outcome,
        "odds": odds,
        "stake": stake,
        "confidence": confidence,
    }
    if selection_odds is not None:
        d["selection_odds"] = selection_odds
    if opening_odds is not None:
        d["opening_odds"] = opening_odds
    return d


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


class TestSkipReasons:
    def test_skip_reasons_correctly_aggregated(self):
        skips = [
            {"skip_reason": "confidence below threshold (0.55)"},
            {"skip_reason": "confidence below threshold (0.50)"},
            {"skip_reason": "no edge found"},
            {"skip_reason": "market agent veto: stale odds"},
            {"skip_reason": "ineligible fixture"},
        ]
        service = _make_service([], skips=skips)
        summary = service.compute()
        assert summary.total_skips == 5
        assert summary.skip_reasons["confidence_below_threshold"] == 2
        assert summary.skip_reasons["no_edge"] == 1
        assert summary.skip_reasons["veto"] == 1
        assert summary.skip_reasons["ineligible_fixture"] == 1

    def test_no_signals_reason_normalised(self):
        skips = [{"skip_reason": "no signals available"}]
        service = _make_service([], skips=skips)
        summary = service.compute()
        assert summary.skip_reasons["no_signals_available"] == 1

    def test_unknown_reason_used_as_key(self):
        skips = [{"skip_reason": "some weird reason"}]
        service = _make_service([], skips=skips)
        summary = service.compute()
        assert summary.skip_reasons["some weird reason"] == 1

    def test_missing_skip_reason_becomes_unknown(self):
        skips = [{"skip_reason": None}]
        service = _make_service([], skips=skips)
        summary = service.compute()
        assert summary.skip_reasons["unknown"] == 1

    def test_empty_skips_returns_empty_reasons(self):
        service = _make_service([])
        summary = service.compute()
        assert summary.total_skips == 0
        assert summary.skip_reasons == {}


class TestClvAverage:
    def test_clv_average_computed_correctly(self):
        picks = [
            _pick(outcome="won", selection_odds=2.0, opening_odds=2.5),
            _pick(outcome="lost", selection_odds=1.8, opening_odds=2.0),
        ]
        service = _make_service(picks)
        summary = service.compute()
        # CLV for pick 1: (1/2.5) - (1/2.0) = 0.4 - 0.5 = -0.1
        # CLV for pick 2: (1/2.0) - (1/1.8) = 0.5 - 0.5556 = -0.0556
        # Average: (-0.1 + -0.0556) / 2 = -0.0778
        assert summary.clv_average is not None
        assert summary.clv_average == pytest.approx(-0.0778, abs=0.001)

    def test_clv_average_none_when_no_opening_odds(self):
        picks = [_pick(outcome="won")]
        service = _make_service(picks)
        summary = service.compute()
        assert summary.clv_average is None

    def test_clv_average_none_when_no_picks(self):
        service = _make_service([])
        summary = service.compute()
        assert summary.clv_average is None


class TestCalibrationBuckets:
    def test_calibration_buckets_correct(self):
        picks = [
            _pick(outcome="won", confidence=0.62),
            _pick(outcome="lost", confidence=0.63),
            _pick(outcome="won", confidence=0.68),
            _pick(outcome="won", confidence=0.72),
            _pick(outcome="lost", confidence=0.72),
            _pick(outcome="won", confidence=0.80),
        ]
        service = _make_service(picks)
        summary = service.compute()
        assert len(summary.calibration_buckets) == 4

        bucket_0_60 = next(b for b in summary.calibration_buckets if b["range"] == "0.60-0.65")
        assert bucket_0_60["picks"] == 2
        assert bucket_0_60["won"] == 1
        assert bucket_0_60["win_rate"] == pytest.approx(0.5)

        bucket_0_65 = next(b for b in summary.calibration_buckets if b["range"] == "0.65-0.70")
        assert bucket_0_65["picks"] == 1
        assert bucket_0_65["won"] == 1
        assert bucket_0_65["win_rate"] == pytest.approx(1.0)

        bucket_0_70 = next(b for b in summary.calibration_buckets if b["range"] == "0.70-0.75")
        assert bucket_0_70["picks"] == 2
        assert bucket_0_70["won"] == 1
        assert bucket_0_70["win_rate"] == pytest.approx(0.5)

        bucket_0_75 = next(b for b in summary.calibration_buckets if b["range"] == "0.75+")
        assert bucket_0_75["picks"] == 1
        assert bucket_0_75["won"] == 1
        assert bucket_0_75["win_rate"] == pytest.approx(1.0)

    def test_empty_buckets_excluded(self):
        picks = [
            _pick(outcome="won", confidence=0.62),
        ]
        service = _make_service(picks)
        summary = service.compute()
        assert len(summary.calibration_buckets) == 1
        assert summary.calibration_buckets[0]["range"] == "0.60-0.65"

    def test_pending_picks_excluded_from_calibration(self):
        picks = [
            _pick(outcome=None, confidence=0.62),
        ]
        service = _make_service(picks)
        summary = service.compute()
        assert len(summary.calibration_buckets) == 0

    def test_void_picks_excluded_from_calibration(self):
        picks = [
            _pick(outcome="void", confidence=0.62),
        ]
        service = _make_service(picks)
        summary = service.compute()
        assert len(summary.calibration_buckets) == 0
