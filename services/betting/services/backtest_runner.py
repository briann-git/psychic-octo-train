"""
Replays historical fixtures through the full pipeline to evaluate agent
policy performance without live scheduling or real-time data dependencies.
"""

import csv
import logging
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from betting.adapters.football_data import FootballDataProvider
from betting.adapters.odds_api import OddsApiProvider
from betting.adapters.sqlite_ledger import SqliteLedgerRepository
from betting.config.league_config import LeagueConfigLoader
from betting.config.market_config import MarketConfigLoader
from betting.graph.nodes.ingest import IngestNode
from betting.graph.nodes.ledger import LedgerNode
from betting.graph.nodes.market import MarketNode
from betting.graph.nodes.statistical import StatisticalNode
from betting.graph.nodes.synthesiser import SynthesiserNode
from betting.graph.pipeline import build_pipeline
from betting.graph.state import BettingState
from betting.models.backtest import BacktestConfig, BacktestEquityPoint, BacktestResult
from betting.models.fixture import Fixture
from betting.models.verdict import Verdict
from betting.services.agent_execution_service import AgentExecutionService
from betting.services.agent_recalibration_service import AgentRecalibrationService
from betting.services.agent_repository import AgentRepository
from betting.services.fixture_service import FixtureService
from betting.services.ledger_service import LedgerService
from betting.services.market_service import MarketService
from betting.services.pnl_service import PnlService
from betting.services.result_ingestion_service import ResultIngestionService
from betting.services.statistical_service import StatisticalService

logger = logging.getLogger(__name__)

# Recalibrate after this many settled picks (mirrors MIN_PICKS_FOR_UPDATE)
_RECALIBRATION_BATCH = 5
# Kick-off minus this many hours is the "as-of" point for historical odds
_ODDS_AS_OF_HOURS_BEFORE = 24


class BacktestRunner:
    def __init__(
        self,
        config: BacktestConfig,
        profile_id: str,
        odds_api: OddsApiProvider,
        csv_service,
        stats_provider: FootballDataProvider,
        ledger_repo: SqliteLedgerRepository,
        agent_repo: AgentRepository,
        league_loader: LeagueConfigLoader,
        market_loader: MarketConfigLoader,
        agent_weights: dict[str, float],
        confidence_threshold: float,
        flat_stake: float,
    ) -> None:
        self._config = config
        self._profile_id = profile_id
        self._odds_api = odds_api
        self._csv_service = csv_service
        self._stats_provider = stats_provider
        self._ledger_repo = ledger_repo
        self._agent_repo = agent_repo
        self._league_loader = league_loader
        self._market_loader = market_loader
        self._agent_weights = agent_weights
        self._confidence_threshold = confidence_threshold
        self._flat_stake = flat_stake

    def run(self) -> BacktestResult:
        cfg = self._config
        logger.info(
            "Backtest starting — league=%s season=%s profile=%s",
            cfg.league, cfg.season, self._profile_id,
        )

        fixtures_with_results = self._load_fixtures_from_csv()
        if not fixtures_with_results:
            logger.warning("No completed fixtures found for %s %s", cfg.league, cfg.season)
            return BacktestResult(
                config=cfg,
                fixtures_processed=0,
                picks_made=0,
                equity_curve=[],
                pnl_summary={},
            )

        active_market_ids = [m.id for m in self._market_loader.active_markets()]
        statistical_service = StatisticalService(
            stats_provider=self._stats_provider,
            market_loader=self._market_loader,
        )
        market_service = MarketService(
            ledger_repo=self._ledger_repo,
            market_loader=self._market_loader,
        )
        ledger_service = LedgerService(repository=self._ledger_repo)
        agent_execution_service = AgentExecutionService(
            agent_repo=self._agent_repo,
            flat_stake=self._flat_stake,
            profile_id=self._profile_id,
        )
        recalibration_service = AgentRecalibrationService(agent_repo=self._agent_repo)
        result_ingestion = ResultIngestionService(
            odds_api=self._odds_api,
            ledger_repo=self._ledger_repo,
            market_loader=self._market_loader,
            csv_service=self._csv_service,
            settlement_lag_hours=0,  # immediate settlement — results are known
            agent_repo=self._agent_repo,
        )
        pnl_service = PnlService(ledger_repo=self._ledger_repo)

        pipeline = build_pipeline(
            ingest_node=IngestNode(
                FixtureService(
                    fixture_provider=self._odds_api,
                    odds_provider=self._odds_api,
                    supported_leagues=[cfg.league],
                )
            ),
            statistical_node=StatisticalNode(statistical_service),
            market_node=MarketNode(market_service),
            synthesiser_node=SynthesiserNode(
                weights=self._agent_weights,
                confidence_threshold=self._confidence_threshold,
            ),
            ledger_node=LedgerNode(
                ledger_service,
                profile_id=self._profile_id,
                profile_type="backtest",
            ),
        )

        fixtures_processed = 0
        picks_made = 0
        picks_since_last_recal = 0
        equity_curve: list[BacktestEquityPoint] = []

        for fixture, result in fixtures_with_results:
            as_of = fixture.kickoff - timedelta(hours=_ODDS_AS_OF_HOURS_BEFORE)
            cutoff_iso = as_of.isoformat()

            snapshots = self._odds_api.fetch_historical_odds_for_match(
                fixture=fixture,
                as_of=as_of,
                markets=active_market_ids,
            )
            if not snapshots:
                logger.debug(
                    "No historical odds for %s vs %s (%s) — skipping",
                    fixture.home_team, fixture.away_team, fixture.kickoff.date(),
                )
                fixtures_processed += 1
                continue

            for odds in snapshots:
                initial_state: BettingState = {
                    "fixture": asdict(fixture),
                    "markets": active_market_ids,
                    "odds_snapshot": asdict(odds),
                    "eligible": True,
                    "cutoff_date": cutoff_iso,
                    "statistical_signal": None,
                    "market_signal": None,
                    "verdict": None,
                    "recorded": False,
                    "errors": [],
                }

                try:
                    final_state = pipeline.invoke(initial_state)
                except Exception as exc:
                    logger.error(
                        "Pipeline error for %s vs %s market %s: %s",
                        fixture.home_team, fixture.away_team, odds.market, exc,
                    )
                    continue

                verdict_dict = final_state.get("verdict")
                if verdict_dict and verdict_dict.get("recommendation") == "back":
                    verdict = Verdict.from_dict(verdict_dict)
                    signals = [
                        s for s in [
                            final_state.get("statistical_signal"),
                            final_state.get("market_signal"),
                        ]
                        if s is not None
                    ]
                    try:
                        agent_execution_service.execute(verdict, fixture, odds, signals)
                        picks_made += 1
                        picks_since_last_recal += 1
                    except Exception as exc:
                        logger.error("AgentExecutionService error: %s", exc)

            # Immediately settle this fixture using the known result
            try:
                result_ingestion.settle_fixture_directly(
                    fixture=fixture,
                    result=result,
                    profile_id=self._profile_id,
                )
            except Exception as exc:
                logger.error("Settlement error for %s vs %s: %s", fixture.home_team, fixture.away_team, exc)

            # Recalibrate agents after every N settled picks
            if picks_since_last_recal >= _RECALIBRATION_BATCH:
                try:
                    recalibration_service.recalibrate_all(
                        since=fixture.kickoff - timedelta(days=365),
                        profile_id=self._profile_id,
                    )
                except Exception as exc:
                    logger.warning("Recalibration error: %s", exc)
                picks_since_last_recal = 0

            # Record equity curve point (sum of all agent bankrolls)
            bankroll = self._total_bankroll()
            recommendation = "back" if picks_made > 0 else "skip"
            if snapshots and final_state.get("verdict"):
                recommendation = final_state["verdict"].get("recommendation", "skip")
            equity_curve.append(BacktestEquityPoint(
                fixture_date=fixture.kickoff,
                home_team=fixture.home_team,
                away_team=fixture.away_team,
                market=snapshots[0].market if snapshots else "",
                recommendation=recommendation,
                outcome=self._last_settled_outcome(fixture),
                bankroll=bankroll,
            ))

            fixtures_processed += 1

        # Final recalibration pass
        try:
            recalibration_service.recalibrate_all(
                since=datetime.min.replace(tzinfo=timezone.utc),
                profile_id=self._profile_id,
            )
        except Exception as exc:
            logger.warning("Final recalibration error: %s", exc)

        pnl_summary = {}
        try:
            summary = pnl_service.compute(profile_id=self._profile_id)
            pnl_summary = asdict(summary)
        except Exception as exc:
            logger.warning("PnL computation error: %s", exc)

        logger.info(
            "Backtest complete — fixtures: %d, picks: %d",
            fixtures_processed, picks_made,
        )

        return BacktestResult(
            config=cfg,
            fixtures_processed=fixtures_processed,
            picks_made=picks_made,
            equity_curve=equity_curve,
            pnl_summary=pnl_summary,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_fixtures_from_csv(self) -> list[tuple[Fixture, dict]]:
        """
        Reads the season CSV and returns (Fixture, result_dict) pairs for all
        completed matches, sorted chronologically. Applies date_from / date_to
        filters from the config if set.
        """
        cfg = self._config
        try:
            csv_path = self._csv_service.get(cfg.league, cfg.season)
        except Exception as exc:
            logger.error("Cannot load CSV for %s %s: %s", cfg.league, cfg.season, exc)
            return []

        team_name_map = self._league_loader.team_names(cfg.league)
        rows = []

        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get("FTHG") or not row.get("FTAG"):
                    continue  # unplayed fixture

                date_raw = row.get("Date", "").strip()
                if not date_raw:
                    continue
                match_date = None
                for _fmt in ("%d/%m/%Y", "%d/%m/%y"):
                    try:
                        match_date = datetime.strptime(date_raw, _fmt).replace(
                            hour=15, minute=0, tzinfo=timezone.utc
                        )
                        break
                    except ValueError:
                        pass
                if match_date is None:
                    continue

                if cfg.date_from and match_date < cfg.date_from:
                    continue
                if cfg.date_to and match_date > cfg.date_to:
                    continue

                home_raw = row.get("HomeTeam", "").strip()
                away_raw = row.get("AwayTeam", "").strip()
                home = team_name_map.get(home_raw, home_raw)
                away = team_name_map.get(away_raw, away_raw)

                if not home or not away:
                    continue

                ftr = row.get("FTR", "").strip()
                fthg = int(float(row["FTHG"]))
                ftag = int(float(row["FTAG"]))

                fixture = Fixture(
                    id=f"bt_{cfg.league}_{home}_{away}_{date_raw.replace('/', '')}",
                    home_team=home,
                    away_team=away,
                    league=cfg.league,
                    season=cfg.season,
                    matchday=0,
                    kickoff=match_date,
                )
                result = {"ftr": ftr, "fthg": fthg, "ftag": ftag}
                rows.append((fixture, result))

        rows.sort(key=lambda x: x[0].kickoff)
        logger.info("BacktestRunner: loaded %d completed fixtures", len(rows))
        return rows

    def _total_bankroll(self) -> float:
        """Sum of all non-decommissioned agent bankrolls for this profile."""
        agents = self._agent_repo.get_all_agents(profile_id=self._profile_id)
        return sum(a.bankroll for a in agents if not a.is_decommissioned)

    def _last_settled_outcome(self, fixture: Fixture) -> str | None:
        """Return outcome of the most recently settled pick for this fixture."""
        try:
            pick = self._ledger_repo.get_by_fixture(fixture.id, profile_id=self._profile_id)
            if pick and "outcome" in pick:
                return pick["outcome"]
        except Exception:
            pass
        return None
