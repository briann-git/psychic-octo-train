"""
Entry point for the autonomous football betting pipeline.
Runs via APScheduler at 08:00 UTC daily.
"""

import logging
from dataclasses import asdict

from apscheduler.schedulers.blocking import BlockingScheduler

from betting.adapters.fbref import FBrefProvider
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
from betting.services.fixture_service import FixtureService
from betting.services.ledger_service import LedgerService
from betting.services.statistical_service import StatisticalService

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


def run_pipeline() -> None:
    logger.info("Pipeline run started")

    # 1. Instantiate concrete adapters
    odds_api = OddsApiProvider(api_key=settings.odds_api_key)
    ledger_repo = SqliteLedgerRepository(
        db_path=settings.db_path,
        flat_stake=settings.flat_stake,
    )

    # 2. Instantiate services with injected providers
    fixture_service = FixtureService(
        fixture_provider=odds_api,
        odds_provider=odds_api,
        supported_leagues=settings.supported_leagues,
        min_lead_hours=settings.min_lead_hours,
        max_lead_hours=settings.max_lead_hours,
    )
    statistical_service = StatisticalService(stats_provider=FBrefProvider())
    ledger_service = LedgerService(repository=ledger_repo)

    # 3. Instantiate nodes with injected services
    pipeline = build_pipeline(
        ingest_node=IngestNode(fixture_service),
        statistical_node=StatisticalNode(statistical_service),
        synthesiser_node=SynthesiserNode(),
        ledger_node=LedgerNode(ledger_service),
    )

    # 4. Fetch eligible fixtures and invoke one graph run per fixture
    eligible = fixture_service.get_eligible_fixtures(markets=["double_chance"])
    logger.info("Found %d eligible fixture(s)", len(eligible))

    for fixture, odds in eligible:
        logger.info(
            "Processing fixture %s: %s vs %s, kickoff %s",
            fixture.id,
            fixture.home_team,
            fixture.away_team,
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
            logger.error("Unhandled error processing fixture %s: %s", fixture.id, exc)

    logger.info("Pipeline run completed")


if __name__ == "__main__":
    # APScheduler cron — runs daily at 08:00 UTC
    scheduler = BlockingScheduler()
    scheduler.add_job(run_pipeline, "cron", hour=8, minute=0)
    scheduler.start()
