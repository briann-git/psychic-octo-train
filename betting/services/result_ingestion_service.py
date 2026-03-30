"""Result ingestion service — fetches completed match results from The Odds API
and settles pending picks in the ledger."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from betting.adapters.odds_api import OddsApiProvider
from betting.interfaces.ledger_repository import ILedgerRepository

logger = logging.getLogger(__name__)


@dataclass
class SettlementSummary:
    settled: int = 0
    won: int = 0
    lost: int = 0
    void: int = 0
    still_pending: int = 0


class ResultIngestionService:
    def __init__(
        self,
        odds_api: OddsApiProvider,
        ledger_repo: ILedgerRepository,
        settlement_lag_hours: int = 12,
    ) -> None:
        self._odds_api = odds_api
        self._ledger = ledger_repo
        self._settlement_lag_hours = settlement_lag_hours

    def settle_pending_picks(
        self, leagues: list[str]
    ) -> SettlementSummary:
        """
        Fetches recent results from the Odds API, matches against pending picks,
        and marks each as won/lost/void.
        Returns a summary of what was settled.
        """
        pending = self._ledger.get_pending_picks()
        if not pending:
            logger.info("No pending picks to settle")
            return SettlementSummary()

        # Fetch results for all active leagues
        results = self._load_results(leagues)

        now = datetime.now(tz=timezone.utc)
        summary = SettlementSummary()

        for pick in pending:
            kickoff = datetime.fromisoformat(pick["kickoff"])
            if kickoff.tzinfo is None:
                kickoff = kickoff.replace(tzinfo=timezone.utc)

            # Not enough time elapsed — leave pending
            if (now - kickoff).total_seconds() < self._settlement_lag_hours * 3600:
                summary.still_pending += 1
                continue

            result_key = (pick["home_team"], pick["away_team"])
            result = results.get(result_key)

            if result is None:
                # API not yet returning result — leave pending
                logger.debug(
                    "Result not yet available for %s vs %s",
                    pick["home_team"], pick["away_team"],
                )
                summary.still_pending += 1
                continue

            outcome = self._determine_outcome(pick["selection"], result)
            self._ledger.settle_pick(pick["id"], outcome)

            summary.settled += 1
            if outcome == "won":
                summary.won += 1
            elif outcome == "lost":
                summary.lost += 1
            else:
                summary.void += 1

        return summary

    def _load_results(self, leagues: list[str]) -> dict[tuple[str, str], dict]:
        """
        Fetches completed results for all leagues.
        Returns dict keyed by (home_team, away_team) -> {ftr}.
        """
        results: dict[tuple[str, str], dict] = {}
        for league in leagues:
            try:
                events = self._odds_api.fetch_results(league, days_from=2)
                for event in events:
                    ftr = self._ftr_from_scores(event)
                    key = (event["home_team"], event["away_team"])
                    results[key] = {"ftr": ftr}
            except Exception as exc:
                logger.error("Failed to fetch results for %s: %s", league, exc)
        return results

    def _ftr_from_scores(self, event: dict) -> str:
        scores = {s["name"]: int(s["score"]) for s in event.get("scores", [])}
        home = scores.get(event["home_team"], 0)
        away = scores.get(event["away_team"], 0)
        if home > away:
            return "H"
        elif away > home:
            return "A"
        return "D"

    def _determine_outcome(self, selection: str, result: dict) -> str:
        """
        Maps selection + FTR to won/lost/void.

        DC outcomes:
          "1X" wins on H or D (FTR in ["H", "D"])
          "12" wins on H or A (FTR in ["H", "A"])
          "X2" wins on D or A (FTR in ["D", "A"])
        """
        ftr = result.get("ftr", "")
        if not ftr:
            return "void"

        winning_ftrs = {
            "1X": {"H", "D"},
            "12": {"H", "A"},
            "X2": {"D", "A"},
        }
        if selection not in winning_ftrs:
            return "void"

        return "won" if ftr in winning_ftrs[selection] else "lost"
