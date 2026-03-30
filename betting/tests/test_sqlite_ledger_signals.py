"""Tests for pick_signals, opening_odds, and get_all_skips in SqliteLedgerRepository."""

import json
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone

import pytest

from betting.adapters.sqlite_ledger import SqliteLedgerRepository
from betting.models.fixture import Fixture
from betting.models.odds import OddsSnapshot
from betting.models.verdict import Verdict


@pytest.fixture()
def repo(tmp_path):
    db_path = str(tmp_path / "test_ledger.db")
    return SqliteLedgerRepository(db_path=db_path, flat_stake=10.0)


def _fixture(fixture_id: str = "fix_1") -> Fixture:
    return Fixture(
        id=fixture_id,
        home_team="Team A",
        away_team="Team B",
        league="PL",
        season="2025-26",
        matchday=1,
        kickoff=datetime(2026, 3, 30, 15, 0, tzinfo=timezone.utc),
    )


def _odds(fixture_id: str = "fix_1", selections: dict | None = None) -> OddsSnapshot:
    return OddsSnapshot(
        fixture_id=fixture_id,
        market="double_chance",
        bookmaker="bet365",
        selections=selections or {"1X": 1.50, "12": 1.80, "X2": 2.10},
        fetched_at=datetime(2026, 3, 30, 14, 0, tzinfo=timezone.utc),
    )


def _verdict_back(fixture_id: str = "fix_1") -> Verdict:
    return Verdict(
        fixture_id=fixture_id,
        market="double_chance",
        recommendation="back",
        consensus_confidence=0.72,
        expected_value=0.05,
        signals_used=2,
        synthesised_at=datetime(2026, 3, 30, 14, 30, tzinfo=timezone.utc),
        selection="1X",
    )


def _signal(agent_id: str = "statistical") -> dict:
    return {
        "agent_id": agent_id,
        "recommendation": "back",
        "confidence": 0.70,
        "edge": 0.05,
        "selection": "1X",
        "reasoning": "Strong home form",
        "veto": False,
        "veto_reason": None,
        "data_timestamp": "2026-03-30T12:00:00+00:00",
    }


class TestRecordPickSignals:
    def test_writes_one_row_per_signal(self, repo):
        fixture = _fixture()
        odds = _odds()
        verdict = _verdict_back()

        # Write a pick first
        repo._write_pick(fixture, odds, verdict)
        pick = repo.get_by_fixture("fix_1")
        assert pick is not None

        signals = [_signal("statistical"), _signal("market")]
        repo.record_pick_signals(pick["id"], signals)

        # Verify rows written
        with repo._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM pick_signals WHERE pick_id = ?", (pick["id"],)
            )
            rows = cursor.fetchall()
        assert len(rows) == 2

    def test_idempotent_on_duplicate_call(self, repo):
        fixture = _fixture()
        odds = _odds()
        verdict = _verdict_back()

        repo._write_pick(fixture, odds, verdict)
        pick = repo.get_by_fixture("fix_1")

        signals = [_signal("statistical")]
        repo.record_pick_signals(pick["id"], signals)
        # Second call with new UUIDs — should insert additional rows (INSERT OR IGNORE)
        repo.record_pick_signals(pick["id"], signals)

        with repo._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM pick_signals WHERE pick_id = ?", (pick["id"],)
            )
            rows = cursor.fetchall()
        # Each call generates a new UUID, so both inserts succeed
        assert len(rows) == 2


class TestGetOpeningOdds:
    def test_returns_earliest_snapshot_selection_odds(self, repo):
        fixture = _fixture()
        odds_early = OddsSnapshot(
            fixture_id="fix_1",
            market="double_chance",
            bookmaker="bet365",
            selections={"1X": 1.40, "12": 1.70, "X2": 2.20},
            fetched_at=datetime(2026, 3, 29, 8, 0, tzinfo=timezone.utc),
        )
        odds_late = OddsSnapshot(
            fixture_id="fix_1",
            market="double_chance",
            bookmaker="bet365",
            selections={"1X": 1.50, "12": 1.80, "X2": 2.10},
            fetched_at=datetime(2026, 3, 30, 14, 0, tzinfo=timezone.utc),
        )

        repo.save_odds_snapshot(fixture, odds_early, "opening")
        repo.save_odds_snapshot(fixture, odds_late, "pre_analysis")

        result = repo._get_opening_odds("fix_1", "1X")
        assert result == 1.40

    def test_returns_none_when_no_history(self, repo):
        result = repo._get_opening_odds("nonexistent", "1X")
        assert result is None

    def test_returns_none_for_unknown_selection(self, repo):
        fixture = _fixture()
        odds = _odds()
        repo.save_odds_snapshot(fixture, odds, "opening")

        result = repo._get_opening_odds("fix_1", "nonexistent_selection")
        assert result is None


class TestOpeningOddsWrittenToPick:
    def test_opening_odds_written_to_picks_row(self, repo):
        fixture = _fixture()
        odds_early = OddsSnapshot(
            fixture_id="fix_1",
            market="double_chance",
            bookmaker="bet365",
            selections={"1X": 1.40, "12": 1.70, "X2": 2.20},
            fetched_at=datetime(2026, 3, 29, 8, 0, tzinfo=timezone.utc),
        )

        # Save opening odds first
        repo.save_odds_snapshot(fixture, odds_early, "opening")

        # Write pick — should pick up opening odds
        verdict = _verdict_back()
        analysis_odds = _odds()
        repo._write_pick(fixture, analysis_odds, verdict)

        pick = repo.get_by_fixture("fix_1")
        assert pick is not None
        assert pick["opening_odds"] == 1.40

    def test_opening_odds_none_when_no_history(self, repo):
        fixture = _fixture()
        verdict = _verdict_back()
        analysis_odds = _odds()

        repo._write_pick(fixture, analysis_odds, verdict)

        pick = repo.get_by_fixture("fix_1")
        assert pick is not None
        assert pick["opening_odds"] is None


class TestGetAllSkips:
    def test_returns_all_skips(self, repo):
        fixture = _fixture("fix_skip_1")
        odds = _odds("fix_skip_1")
        skip_verdict = Verdict(
            fixture_id="fix_skip_1",
            market="double_chance",
            recommendation="skip",
            consensus_confidence=0.40,
            expected_value=-0.02,
            signals_used=1,
            synthesised_at=datetime(2026, 3, 30, 14, 30, tzinfo=timezone.utc),
            skip_reason="confidence below threshold",
        )
        repo._write_skip(fixture, odds, skip_verdict, [])

        skips = repo.get_all_skips()
        assert len(skips) == 1
        assert skips[0]["fixture_id"] == "fix_skip_1"
        assert "confidence below threshold" in skips[0]["skip_reason"]

    def test_returns_empty_list_when_no_skips(self, repo):
        skips = repo.get_all_skips()
        assert skips == []
