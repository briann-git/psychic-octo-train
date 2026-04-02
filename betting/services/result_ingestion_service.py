"""Result ingestion service — fetches completed match results from The Odds API
and settles pending picks in the ledger."""

import csv
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from betting.adapters.odds_api import OddsApiProvider
from betting.config.market_config import MarketConfigLoader
from betting.interfaces.ledger_repository import ILedgerRepository
from betting.markets.evaluator import OutcomeEvaluator

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
        market_loader: MarketConfigLoader | None = None,
        csv_service=None,
        settlement_lag_hours: int = 12,
        agent_repo=None,
    ) -> None:
        self._odds_api = odds_api
        self._ledger = ledger_repo
        self._market_loader = market_loader or MarketConfigLoader()
        self._csv_service = csv_service
        self._settlement_lag_hours = settlement_lag_hours
        self._evaluator = OutcomeEvaluator()
        self._agent_repo = agent_repo

    def settle_pending_picks(
        self,
        leagues: list[str],
        season: str | None = None,
    ) -> SettlementSummary:
        """
        Fetches recent results from the Odds API, matches against pending picks,
        and marks each as won/lost/void.
        Returns a summary of what was settled.
        """
        if season is None:
            from betting.utils import current_season
            season = current_season()
        pending = self._ledger.get_pending_picks()
        if not pending:
            logger.info("No pending picks to settle")
            # Still settle agent picks even if no main picks are pending
            if self._agent_repo is not None:
                results = self._load_results(leagues, season)
                self._settle_agent_picks(results, datetime.now(tz=timezone.utc))
            return SettlementSummary()

        # Fetch results for all active leagues
        results = self._load_results(leagues, season)

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

            outcome = self._determine_outcome(pick["selection"], pick["market"], result)
            self._ledger.settle_pick(pick["id"], outcome)

            summary.settled += 1
            if outcome == "won":
                summary.won += 1
            elif outcome == "lost":
                summary.lost += 1
            else:
                summary.void += 1

        # Settle agent picks from the same results
        if self._agent_repo is not None:
            self._settle_agent_picks(results, now)

        return summary

    def _load_results(self, leagues: list[str], season: str) -> dict[tuple[str, str], dict]:
        """
        Routes settlement data fetching by market settlement_source.
        Merges API and CSV results into a single dict keyed by (home_team, away_team).
        Result dicts carry all available fields: ftr, fthg, ftag, hy, ay, hr, ar.
        """
        active = self._market_loader.active_markets()
        needs_api = any(m.settlement_source == "api" for m in active)
        needs_csv = any(m.settlement_source == "csv" for m in active)

        results: dict[tuple[str, str], dict] = {}

        if needs_api:
            api_results = self._load_from_api(leagues)
            for key, val in api_results.items():
                results.setdefault(key, {}).update(val)

        if needs_csv and self._csv_service:
            csv_results = self._load_from_csv(leagues, season)
            for key, val in csv_results.items():
                results.setdefault(key, {}).update(val)
        elif needs_csv and not self._csv_service:
            logger.error("CSV settlement required but no CsvDownloadService injected")

        return results

    def _load_from_api(self, leagues: list[str]) -> dict[tuple[str, str], dict]:
        results: dict[tuple[str, str], dict] = {}
        for league in leagues:
            try:
                events = self._odds_api.fetch_results(league, days_from=2)
                for event in events:
                    ftr = self._ftr_from_scores(event)
                    scores = {s["name"]: int(s["score"]) for s in event.get("scores", [])}
                    fthg = scores.get(event["home_team"], 0)
                    ftag = scores.get(event["away_team"], 0)
                    key = (event["home_team"], event["away_team"])
                    results[key] = {"ftr": ftr, "fthg": fthg, "ftag": ftag}
            except Exception as exc:
                logger.error("Failed to fetch results for %s: %s", league, exc)
        return results

    def _load_from_csv(self, leagues: list[str], season: str) -> dict[tuple[str, str], dict]:
        results: dict[tuple[str, str], dict] = {}
        for league in leagues:
            try:
                csv_path = self._csv_service.get(league, season)
                with open(csv_path, encoding="utf-8-sig", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if not row.get("FTHG"):
                            continue
                        home = row.get("HomeTeam", "").strip()
                        away = row.get("AwayTeam", "").strip()
                        if not home or not away:
                            continue
                        key = (home, away)
                        results[key] = {
                            "hy": int(row["HY"]) if row.get("HY") else None,
                            "ay": int(row["AY"]) if row.get("AY") else None,
                            "hr": int(row["HR"]) if row.get("HR") else None,
                            "ar": int(row["AR"]) if row.get("AR") else None,
                        }
            except Exception as exc:
                logger.error("Failed to load CSV results for %s: %s", league, exc)
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

    def _determine_outcome(self, selection_id: str, market_id: str, result: dict) -> str:
        """
        Delegates outcome evaluation to the OutcomeEvaluator via MarketConfigLoader.
        """
        selection = self._market_loader.get_selection(market_id, selection_id)
        if not selection:
            logger.warning(
                "Selection %r not found in market %r — voiding pick",
                selection_id, market_id,
            )
            return "void"
        return self._evaluator.evaluate(selection, result)

    def _settle_agent_picks(
        self,
        results: dict[tuple[str, str], dict],
        now: datetime,
    ) -> None:
        """
        Settles agent_picks rows from results dict.
        Updates agent bankroll on won/void picks.
        """
        agents = self._agent_repo.get_all_agents()
        for agent in agents:
            unsettled = self._agent_repo.get_unsettled_agent_picks(agent.id)
            for pick in unsettled:
                kickoff = datetime.fromisoformat(pick["kickoff"])
                if kickoff.tzinfo is None:
                    kickoff = kickoff.replace(tzinfo=timezone.utc)
                if (now - kickoff).total_seconds() < self._settlement_lag_hours * 3600:
                    continue

                result_key = (pick["home_team"], pick["away_team"])
                result = results.get(result_key)
                if result is None:
                    continue

                selection = self._market_loader.get_selection(
                    pick["market"], pick["selection"]
                )
                outcome = self._evaluator.evaluate(selection, result) if selection else "void"

                # CLV = implied(opening) - implied(analysis)
                clv = None
                opening_odds = pick.get("opening_odds")
                analysis_odds = pick.get("odds")
                if opening_odds and analysis_odds and opening_odds > 0 and analysis_odds > 0:
                    clv = (1.0 / opening_odds) - (1.0 / analysis_odds)

                # P&L
                if outcome == "won":
                    pnl = pick["odds"] * pick["stake"] - pick["stake"]
                elif outcome == "void":
                    pnl = 0.0
                else:
                    pnl = -pick["stake"]

                self._agent_repo.settle_agent_pick(pick["id"], outcome, clv, pnl)

                # Update bankroll
                if outcome == "won":
                    agent.bankroll += pick["odds"] * pick["stake"]
                elif outcome == "void":
                    agent.bankroll += pick["stake"]
                agent.total_settled += 1
                self._agent_repo.save_agent(agent)
