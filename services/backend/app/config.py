import os

DB_PATH = os.environ.get("DB_PATH", "/data/db/ledger.db")
LOG_DIR = os.environ.get("LOG_DIR", "/data/logs")
LOG_FILE = os.path.join(LOG_DIR, "scheduler.log")
HEARTBEAT_DIR = os.environ.get("HEARTBEAT_DIR", "/data/heartbeat")
HEARTBEAT_FILE = os.path.join(HEARTBEAT_DIR, "scheduler.json")
SCHEDULE_FILE = os.path.join(HEARTBEAT_DIR, "schedule.json")
QUOTA_FILE = os.path.join(HEARTBEAT_DIR, "odds_quota.json")

HEARTBEAT_STALE_SECONDS = 15 * 60  # 15 min window; heartbeat fires every 10 min

SAFE_CONFIG_KEYS = {
    "DB_PATH", "CONFIDENCE_THRESHOLD", "FLAT_STAKE",
    "MIN_LEAD_HOURS", "MAX_LEAD_HOURS", "LOG_LEVEL",
    "BACKUP_HOUR", "MORNING_HOUR",
    "RUN_INTERVAL_HOURS", "MAX_ANALYSIS_LEAD_HOURS",
    "CALENDAR_LOOKAHEAD_DAYS", "CALENDAR_REFRESH_HOUR",
    "BETTING_LEAGUES_CONFIG", "BETTING_MARKETS_CONFIG",
    "CSV_CACHE_DIR", "CSV_MAX_AGE_HOURS",
}
