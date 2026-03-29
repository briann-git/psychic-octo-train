"""
Entry point for the autonomous football betting pipeline.
Runs via APScheduler at 08:00 UTC daily.
"""

import logging
from dataclasses import asdict

from apscheduler.schedulers.blocking import BlockingScheduler

from betting.adapters.football_data import FootballDataProvider
from betting.adapters.odds_api import OddsApiProvider
from betting.adapters.sqlite_ledger import SqliteLedgerRepository
from betting.logging_config import configure_logging
from betting.config import settings
from betting.graph.nodes.ingest import IngestNode
from betting.graph.nodes.ledger import LedgerNode
from betting.graph.nodes.statistical import StatisticalNode
from betting.graph.nodes.synthesiser import SynthesiserNode
from betting.graph.pipeline import build_pipeline
from betting.graph.state import BettingState
from betting.services.csv_download_service import CsvDownloadService
from betting.services.fixture_service import FixtureService
from betting.services.ledger_service import LedgerService
from betting.services.statistical_service import StatisticalService
from betting.utils import current_season

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


def download_season_data(
    csv_service: CsvDownloadService,
    leagues: list[str],
    season: str,
) -> None:
    """
    Pre-downloads CSVs for all supported leagues.
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


def run_pipeline() -> None:
    logger.info("Pipeline run started")

    season = current_season()

    # Adapters
    odds_api = OddsApiProvider(api_key=settings.odds_api_key)
    csv_service = CsvDownloadService(
        cache_dir=settings.csv_cache_dir,
        max_age_hours=settings.csv_max_age_hours,
    )
    ledger_repo = SqliteLedgerRepository(
        db_path=settings.db_path,
        flat_stake=settings.flat_stake,
    )

    # Pre-download CSVs
    download_season_data(csv_service, settings.supported_leagues, season)

    # Services
    fixture_service = FixtureService(
        fixture_provider=odds_api,
        odds_provider=odds_api,
        supported_leagues=settings.supported_leagues,
        min_lead_hours=settings.min_lead_hours,
        max_lead_hours=settings.max_lead_hours,
    )
    statistical_service = StatisticalService(
        stats_provider=FootballDataProvider(csv_service=csv_service)
    )
    ledger_service = LedgerService(repository=ledger_repo)

    # Graph
    pipeline = build_pipeline(
        ingest_node=IngestNode(fixture_service),
        statistical_node=StatisticalNode(statistical_service),
        synthesiser_node=SynthesiserNode(),
        ledger_node=LedgerNode(ledger_service),
    )

    # Run
    eligible = fixture_service.get_eligible_fixtures(markets=["double_chance"])
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
            "verdict": None,
            "recorded": False,
            "errors": [],
        }
        try:
            pipeline.invoke(initial_state)
        except Exception as exc:
            logger.error("Unhandled error for fixture %s: %s", fixture.id, exc)

    logger.info("Pipeline run completed")


if __name__ == "__main__":
    # APScheduler cron — runs daily at 08:00 UTC
    scheduler = BlockingScheduler()
    scheduler.add_job(run_pipeline, "cron", hour=8, minute=0)
    scheduler.start()
