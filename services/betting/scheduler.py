"""
Entry point for the autonomous football betting pipeline.
Runs via APScheduler on a daily cron schedule.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.blocking import BlockingScheduler

from betting.adapters.football_data import FootballDataProvider
from betting.adapters.odds_api import OddsApiProvider
from betting.adapters.sqlite_ledger import SqliteLedgerRepository
from betting.config.league_config import LeagueConfigLoader
from betting.config.market_config import MarketConfigLoader
from betting.logging_config import configure_logging
from betting.config import settings
from betting.graph.nodes.ingest import IngestNode
from betting.graph.nodes.ledger import LedgerNode
from betting.graph.nodes.market import MarketNode
from betting.graph.nodes.statistical import StatisticalNode
from betting.graph.nodes.synthesiser import SynthesiserNode
from betting.graph.pipeline import build_pipeline
from betting.graph.state import BettingState
from betting.services.backup_service import BackupService
from betting.services.csv_download_service import CsvDownloadService
from betting.services.fixture_calendar_service import FixtureCalendarService
from betting.services.fixture_service import FixtureService
from betting.services.ledger_service import LedgerService
from betting.services.market_service import MarketService
from betting.services.pnl_service import PnlService
from betting.services.result_ingestion_service import ResultIngestionService
from betting.services.statistical_service import StatisticalService
from betting.services.agent_repository import AgentRepository
from betting.services.agent_execution_service import AgentExecutionService
from betting.services.agent_recalibration_service import AgentRecalibrationService
from betting.utils import current_season

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@dataclass
class _Components:
    odds_api: OddsApiProvider
    csv_service: CsvDownloadService
    ledger_repo: SqliteLedgerRepository
    fixture_service: FixtureService
    stats_provider: FootballDataProvider
    league_loader: LeagueConfigLoader
    market_loader: MarketConfigLoader
    active_leagues: list[str]
    season: str


def _build_components() -> _Components:
    """
    Constructs and returns shared adapters and services.
    Call once per job to get fresh instances with a warm cache.
    """
    league_loader = LeagueConfigLoader()
    market_loader = MarketConfigLoader()
    active_leagues = [l.id for l in league_loader.active_leagues()]
    season = current_season()

    odds_api = OddsApiProvider(
        api_key=settings.odds_api_key,
        league_loader=league_loader,
        market_loader=market_loader,
    )
    csv_service = CsvDownloadService(
        cache_dir=settings.csv_cache_dir,
        max_age_hours=settings.csv_max_age_hours,
        league_loader=league_loader,
    )
    ledger_repo = SqliteLedgerRepository(
        db_path=settings.db_path,
        flat_stake=settings.flat_stake,
    )
    fixture_service = FixtureService(
        fixture_provider=odds_api,
        odds_provider=odds_api,
        supported_leagues=active_leagues,
        min_lead_hours=settings.min_lead_hours,
        max_lead_hours=settings.max_lead_hours,
    )
    stats_provider = FootballDataProvider(
        csv_service=csv_service,
        league_loader=league_loader,
    )
    return _Components(
        odds_api=odds_api,
        csv_service=csv_service,
        ledger_repo=ledger_repo,
        fixture_service=fixture_service,
        stats_provider=stats_provider,
        league_loader=league_loader,
        market_loader=market_loader,
        active_leagues=active_leagues,
        season=season,
    )


def download_season_data(
    csv_service: CsvDownloadService,
    leagues: list[str],
    season: str,
) -> None:
    """
    Pre-downloads CSVs for all active leagues.
    Logs success or failure per league.
    Does not raise — a failed download for one league should not
    block analysis of other leagues.
    """
    for league in leagues:
        try:
            path = csv_service.get(league, season)
            logger.info("CSV ready for %s %s: %s", league, season, path)
        except Exception as exc:
            logger.error("Failed to download CSV for %s %s: %s", league, season, exc)


def run_snapshot_job(
    odds_api: OddsApiProvider,
    fixture_service: FixtureService,
    ledger_repo: SqliteLedgerRepository,
    snapshot_type: str,
    market_loader: MarketConfigLoader | None = None,
    leagues: list[str] | None = None,
) -> None:
    """
    Fetches current odds for all eligible fixtures and persists to odds_history.
    Saves one snapshot per market per fixture.
    snapshot_type: "opening" | "intermediate" | "pre_analysis"
    """
    loader = market_loader or MarketConfigLoader()
    active_market_ids = [m.id for m in loader.active_markets()]
    eligible = fixture_service.get_eligible_fixtures_multi(
        markets=active_market_ids,
        leagues=leagues,
    )
    logger.info("Snapshot job (%s): %d fixture(s)", snapshot_type, len(eligible))

    for fixture, odds_list in eligible:
        effective_type = snapshot_type
        if snapshot_type == "opening":
            history = ledger_repo.get_odds_history(fixture.id)
            if any(r["snapshot_type"] == "opening" for r in history):
                effective_type = "intermediate"
        for odds in odds_list:
            try:
                ledger_repo.save_odds_snapshot(fixture, odds, effective_type)
            except Exception as exc:
                logger.error(
                    "Snapshot write failed for %s market %s: %s",
                    fixture.id, odds.market, exc,
                )


def run_backup_job() -> None:
    logger.info("Backup job started")
    backup_service = BackupService(
        db_path=settings.db_path,
        backup_dir=settings.backup_dir,
        oci_namespace=settings.oci_namespace,
        oci_bucket=settings.oci_bucket,
        local_retention_days=settings.backup_local_retention_days,
        remote_retention_days=settings.backup_remote_retention_days,
    )
    try:
        backup_service.run()
        logger.info("Backup job completed")
    except Exception as exc:
        logger.error("Backup job failed: %s", exc)
        # Non-fatal — do not raise, morning job must still run


def run_morning_job() -> None:
    """08:00 — settle yesterday's results, then take opening snapshot."""
    logger.info("Morning job started")
    c = _build_components()

    # 1. Settle pending picks from Odds API
    agent_repo = AgentRepository(db_path=settings.db_path)
    result_service = ResultIngestionService(
        odds_api=c.odds_api,
        ledger_repo=c.ledger_repo,
        market_loader=c.market_loader,
        csv_service=c.csv_service,
        agent_repo=agent_repo,
    )
    settlement = result_service.settle_pending_picks(
        c.active_leagues,
        season=c.season,
    )
    logger.info(
        "Settlement complete — settled: %d, won: %d, lost: %d, void: %d, still_pending: %d",
        settlement.settled, settlement.won, settlement.lost,
        settlement.void, settlement.still_pending,
    )

    # 2. Opening snapshot
    run_snapshot_job(c.odds_api, c.fixture_service, c.ledger_repo, "opening", c.market_loader)
    logger.info("Morning job completed")


def run_analysis() -> None:
    logger.info("Analysis run started")

    c = _build_components()

    leagues_today = _get_active_leagues_today(c)
    if not leagues_today:
        logger.info("Analysis run skipped — no fixtures today")
        return

    # Pre-download CSVs
    download_season_data(c.csv_service, leagues_today, c.season)

    # Pre-analysis snapshot
    run_snapshot_job(c.odds_api, c.fixture_service, c.ledger_repo, "pre_analysis", c.market_loader, leagues=leagues_today)

    # Services
    statistical_service = StatisticalService(
        stats_provider=c.stats_provider,
        market_loader=c.market_loader,
    )
    market_service = MarketService(
        ledger_repo=c.ledger_repo,
        market_loader=c.market_loader,
    )
    ledger_service = LedgerService(repository=c.ledger_repo)

    # Agent execution
    agent_repo = AgentRepository(db_path=settings.db_path)
    agent_execution_service = AgentExecutionService(
        agent_repo=agent_repo,
        flat_stake=settings.flat_stake,
    )

    # Graph
    pipeline = build_pipeline(
        ingest_node=IngestNode(c.fixture_service),
        statistical_node=StatisticalNode(statistical_service),
        market_node=MarketNode(market_service),
        synthesiser_node=SynthesiserNode(
            weights=settings.agent_weights,
            confidence_threshold=settings.confidence_threshold,
        ),
        ledger_node=LedgerNode(ledger_service, paper_trading=settings.paper_trading),
    )

    # Run
    active_market_ids = [m.id for m in c.market_loader.active_markets()]
    eligible = c.fixture_service.get_eligible_fixtures_multi(
        markets=active_market_ids,
        leagues=leagues_today,
    )
    logger.info("Found %d eligible fixture(s)", len(eligible))

    for fixture, odds_list in eligible:
        for odds in odds_list:
            logger.info(
                "Processing %s: %s vs %s, market=%s, kickoff %s",
                fixture.id, fixture.home_team, fixture.away_team,
                odds.market,
                fixture.kickoff.isoformat(),
            )
            initial_state: BettingState = {
                "fixture": asdict(fixture),
                "markets": active_market_ids,
                "odds_snapshot": asdict(odds),
                "eligible": True,
                "statistical_signal": None,
                "market_signal": None,
                "verdict": None,
                "recorded": False,
                "errors": [],
            }
            try:
                final_state = pipeline.invoke(initial_state)

                # Dispatch to bandit agents
                verdict_dict = final_state.get("verdict")
                if verdict_dict and verdict_dict.get("recommendation") == "back":
                    from betting.models.verdict import Verdict as VerdictModel
                    verdict = VerdictModel.from_dict(verdict_dict)
                    signals = [
                        s for s in [
                            final_state.get("statistical_signal"),
                            final_state.get("market_signal"),
                        ]
                        if s is not None
                    ]
                    agent_execution_service.execute(verdict, fixture, odds, signals)
            except Exception as exc:
                logger.error(
                    "Unhandled error for fixture %s market %s: %s",
                    fixture.id, odds.market, exc,
                )

    # P&L summary
    pnl_service = PnlService(ledger_repo=c.ledger_repo)
    summary = pnl_service.compute()
    logger.info(
        "P&L summary — picks: %d (settled: %d, pending: %d) | "
        "won: %d lost: %d void: %d | "
        "win_rate: %.1f%% | staked: %.2f | net: %.2f | ROI: %.1f%% | "
        "CLV: %s",
        summary.total_picks,
        summary.settled,
        summary.pending,
        summary.won,
        summary.lost,
        summary.void,
        summary.win_rate * 100,
        summary.total_staked,
        summary.net_pnl,
        summary.roi * 100,
        f"{summary.clv_average:+.4f}" if summary.clv_average is not None else "n/a",
    )

    if summary.skip_reasons:
        logger.info(
            "Skips today — total: %d | %s",
            summary.total_skips,
            " | ".join(f"{k}: {v}" for k, v in sorted(summary.skip_reasons.items())),
        )

    if summary.calibration_buckets:
        logger.info("Confidence calibration (settled picks):")
        for bucket in summary.calibration_buckets:
            win_rate_str = (
                f"{bucket['win_rate'] * 100:.1f}%"
                if bucket["win_rate"] is not None
                else "n/a"
            )
            logger.info(
                "  %s: %d picks, %d won (%s)",
                bucket["range"], bucket["picks"], bucket["won"], win_rate_str,
            )

    # Per-agent P&L
    agents = agent_repo.get_all_agents()
    for agent in agents:
        roi = ((agent.bankroll - agent.starting_bankroll) / agent.starting_bankroll) * 100
        logger.info(
            "Agent %s — bankroll: %.2f (ROI: %+.1f%%) | picks: %d | "
            "policy: stat=%.2f mkt=%.2f threshold=%.2f updates=%d",
            agent.id,
            agent.bankroll,
            roi,
            agent.total_picks,
            agent.policy.statistical_weight,
            agent.policy.market_weight,
            agent.policy.confidence_threshold,
            agent.policy.update_count,
        )

    logger.info("Analysis run completed")


def run_agent_recalibration() -> None:
    """Weekly agent recalibration — runs after Sunday settlement."""
    logger.info("Agent recalibration started")
    agent_repo = AgentRepository(db_path=settings.db_path)
    recalibration_service = AgentRecalibrationService(agent_repo=agent_repo)

    since = datetime.now(tz=timezone.utc) - timedelta(days=7)
    recalibration_service.recalibrate_all(since=since)
    logger.info("Agent recalibration completed")


def run_calendar_refresh() -> None:
    """
    Weekly job — fetches upcoming fixtures and stores in local calendar.
    Runs Sunday evening so the week ahead is populated before Monday.
    """
    logger.info("Calendar refresh started")
    c = _build_components()
    calendar_service = FixtureCalendarService(
        fixture_provider=c.odds_api,
        ledger_repo=c.ledger_repo,
        lookahead_days=settings.calendar_lookahead_days,
    )
    count = calendar_service.refresh(c.active_leagues)
    logger.info("Calendar refresh completed — %d fixture(s)", count)


def _get_active_leagues_today(c: _Components) -> list[str]:
    """
    Returns the subset of active leagues that have fixtures in today's
    analysis window. No API calls — reads from SQLite only.
    """
    now = datetime.now(tz=timezone.utc)
    from_dt = now + timedelta(hours=settings.min_lead_hours)
    to_dt = now + timedelta(hours=settings.max_lead_hours)

    fixtures = c.ledger_repo.get_calendar_fixtures(
        from_dt=from_dt,
        to_dt=to_dt,
        leagues=c.active_leagues,
    )

    active_today = list({f["league"] for f in fixtures})

    if not active_today:
        calendar_service = FixtureCalendarService(
            fixture_provider=c.odds_api,
            ledger_repo=c.ledger_repo,
            lookahead_days=settings.calendar_lookahead_days,
        )
        upcoming = calendar_service.upcoming_fixture_dates(c.active_leagues)
        if upcoming:
            logger.info(
                "No fixtures in today's window — skipping. "
                "Next fixtures on: %s", ", ".join(upcoming)
            )
        else:
            logger.warning(
                "No fixtures in today's window and calendar appears empty. "
                "Consider running the calendar refresh job manually."
            )

    return active_today


def _run_snapshot_from_fresh(snapshot_type: str) -> None:
    """Builds fresh components and runs a snapshot job. Used by cron lambdas."""
    c = _build_components()
    leagues_today = _get_active_leagues_today(c)
    if not leagues_today:
        logger.info("Snapshot job (%s) skipped — no fixtures today", snapshot_type)
        return
    run_snapshot_job(
        c.odds_api, c.fixture_service, c.ledger_repo,
        snapshot_type, c.market_loader,
        leagues=leagues_today,
    )


HEARTBEAT_DIR = os.environ.get("HEARTBEAT_DIR", "/data/heartbeat")
HEARTBEAT_FILE = os.path.join(HEARTBEAT_DIR, "scheduler.json")


def send_heartbeat() -> None:
    """Write a heartbeat JSON file so the dashboard knows we are alive."""
    os.makedirs(HEARTBEAT_DIR, exist_ok=True)
    payload = {
        "service": "scheduler",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "status": "running",
    }
    tmp_path = HEARTBEAT_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    os.replace(tmp_path, HEARTBEAT_FILE)


def main() -> None:
    # Bootstrap agents on first run
    agent_repo = AgentRepository(db_path=settings.db_path)
    agent_repo.bootstrap_agents()

    scheduler = BlockingScheduler()

    # Heartbeat every 10 minutes so dashboard can verify we are alive
    scheduler.add_job(send_heartbeat, "interval", minutes=10, next_run_time=datetime.now(tz=timezone.utc))

    scheduler.add_job(run_backup_job, "cron", hour=settings.backup_hour, minute=0)
    scheduler.add_job(run_morning_job, "cron", hour=settings.morning_hour, minute=0)
    scheduler.add_job(
        lambda: _run_snapshot_from_fresh("intermediate"),
        "cron", hour=settings.snapshot_hour, minute=0,
    )
    scheduler.add_job(run_analysis, "cron", hour=settings.analysis_hour, minute=0)
    # Weekly calendar refresh — Sunday at configured hour
    scheduler.add_job(
        run_calendar_refresh,
        "cron", day_of_week="sun",
        hour=settings.calendar_refresh_hour, minute=0,
    )
    # Weekly agent recalibration — Sunday before calendar refresh
    recalibration_hour = (settings.calendar_refresh_hour - 1) % 24
    scheduler.add_job(
        run_agent_recalibration,
        "cron", day_of_week="sun",
        hour=recalibration_hour, minute=0,
    )

    # Bootstrap calendar on first run if empty
    logger.info("Bootstrapping fixture calendar on startup")
    try:
        run_calendar_refresh()
    except Exception as exc:
        logger.error("Calendar bootstrap failed: %s", exc)

    scheduler.start()


if __name__ == "__main__":
    main()
