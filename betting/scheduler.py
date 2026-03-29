"""
Entry point for the autonomous football betting pipeline.
Runs via APScheduler on a daily cron schedule.
"""

import logging
from dataclasses import asdict, dataclass

from apscheduler.schedulers.blocking import BlockingScheduler

from betting.adapters.football_data import FootballDataProvider
from betting.adapters.odds_api import OddsApiProvider
from betting.adapters.sqlite_ledger import SqliteLedgerRepository
from betting.config.league_config import LeagueConfigLoader
from betting.logging_config import configure_logging
from betting.config import settings
from betting.graph.nodes.ingest import IngestNode
from betting.graph.nodes.ledger import LedgerNode
from betting.graph.nodes.market import MarketNode
from betting.graph.nodes.statistical import StatisticalNode
from betting.graph.nodes.synthesiser import SynthesiserNode
from betting.graph.pipeline import build_pipeline
from betting.graph.state import BettingState
from betting.services.csv_download_service import CsvDownloadService
from betting.services.fixture_service import FixtureService
from betting.services.ledger_service import LedgerService
from betting.services.market_service import MarketService
from betting.services.statistical_service import StatisticalService
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
    active_leagues: list[str]
    season: str


def _build_components() -> _Components:
    """
    Constructs and returns shared adapters and services.
    Call once per job to get fresh instances with a warm cache.
    """
    league_loader = LeagueConfigLoader()
    active_leagues = [l.id for l in league_loader.active_leagues()]
    season = current_season()

    odds_api = OddsApiProvider(api_key=settings.odds_api_key, league_loader=league_loader)
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
) -> None:
    """
    Fetches current odds for all eligible fixtures and persists to odds_history.
    snapshot_type: "opening" | "intermediate" | "pre_analysis"
    """
    eligible = fixture_service.get_eligible_fixtures(markets=["double_chance"])
    logger.info("Snapshot job (%s): %d fixture(s)", snapshot_type, len(eligible))

    for fixture, odds in eligible:
        try:
            ledger_repo.save_odds_snapshot(fixture, odds, snapshot_type)
        except Exception as exc:
            logger.error("Snapshot write failed for %s: %s", fixture.id, exc)


def run_analysis() -> None:
    logger.info("Analysis run started")

    c = _build_components()

    # Pre-download CSVs
    download_season_data(c.csv_service, c.active_leagues, c.season)

    # Pre-analysis snapshot
    run_snapshot_job(c.odds_api, c.fixture_service, c.ledger_repo, "pre_analysis")

    # Services
    statistical_service = StatisticalService(stats_provider=c.stats_provider)
    market_service = MarketService(ledger_repo=c.ledger_repo)
    ledger_service = LedgerService(repository=c.ledger_repo)

    # Graph
    pipeline = build_pipeline(
        ingest_node=IngestNode(c.fixture_service),
        statistical_node=StatisticalNode(statistical_service),
        market_node=MarketNode(market_service),
        synthesiser_node=SynthesiserNode(
            weights=settings.agent_weights,
            confidence_threshold=settings.confidence_threshold,
        ),
        ledger_node=LedgerNode(ledger_service),
    )

    # Run
    eligible = c.fixture_service.get_eligible_fixtures(markets=["double_chance"])
    logger.info("Found %d eligible fixture(s)", len(eligible))

    for fixture, odds in eligible:
        logger.info(
            "Processing %s: %s vs %s, kickoff %s",
            fixture.id, fixture.home_team, fixture.away_team,
            fixture.kickoff.isoformat(),
        )
        initial_state: BettingState = {
            "fixture": asdict(fixture),
            "markets": ["double_chance"],
            "odds_snapshot": asdict(odds),
            "eligible": True,
            "statistical_signal": None,
            "market_signal": None,
            "verdict": None,
            "recorded": False,
            "errors": [],
        }
        try:
            pipeline.invoke(initial_state)
        except Exception as exc:
            logger.error("Unhandled error for fixture %s: %s", fixture.id, exc)

    logger.info("Analysis run completed")


def _run_snapshot_from_fresh(snapshot_type: str) -> None:
    """Builds fresh components and runs a snapshot job. Used by cron lambdas."""
    c = _build_components()
    run_snapshot_job(c.odds_api, c.fixture_service, c.ledger_repo, snapshot_type)


if __name__ == "__main__":
    scheduler = BlockingScheduler()

    # 08:00 — opening snapshot
    scheduler.add_job(
        lambda: _run_snapshot_from_fresh("opening"),
        "cron", hour=8, minute=0,
    )

    # 12:00 — intermediate snapshot
    scheduler.add_job(
        lambda: _run_snapshot_from_fresh("intermediate"),
        "cron", hour=12, minute=0,
    )

    # 16:00 — pre-analysis snapshot, then full pipeline
    scheduler.add_job(run_analysis, "cron", hour=16, minute=0)

    scheduler.start()
