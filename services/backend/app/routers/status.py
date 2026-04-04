import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import (
    DB_PATH,
    HEARTBEAT_FILE,
    HEARTBEAT_STALE_SECONDS,
    QUOTA_FILE,
    SCHEDULE_FILE,
)
from app.database import get_db

router = APIRouter()


# ─── Heartbeat helpers ────────────────────────────────────────────────────────

def _read_heartbeat() -> dict | None:
    try:
        with open(HEARTBEAT_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _is_scheduler_running() -> bool:
    hb = _read_heartbeat()
    if not hb or "timestamp" not in hb:
        return False
    try:
        ts = datetime.fromisoformat(hb["timestamp"])
        age = (datetime.now(tz=timezone.utc) - ts).total_seconds()
        return age < HEARTBEAT_STALE_SECONDS
    except (ValueError, TypeError):
        return False


# ─── /api/status ─────────────────────────────────────────────────────────────

@router.get("/status")
def get_status():
    heartbeat = _read_heartbeat()
    running = _is_scheduler_running()
    result = {
        "scheduler_running": running,
        "last_run": None,
        "uptime": heartbeat.get("timestamp") if heartbeat else None,
        "db_size": None,
        "active_profile": None,
    }

    if os.path.exists(DB_PATH):
        sz = os.path.getsize(DB_PATH)
        result["db_size"] = f"{sz / (1024 * 1024):.1f} MB"

    try:
        with get_db() as conn:
            row = conn.execute("SELECT MAX(recorded_at) AS lr FROM agent_picks").fetchone()
            if row and row["lr"]:
                result["last_run"] = row["lr"]
            profile_row = conn.execute(
                "SELECT * FROM profiles WHERE is_active = 1 LIMIT 1"
            ).fetchone()
            if profile_row:
                result["active_profile"] = dict(profile_row)
    except Exception:
        pass

    return result


# ─── /api/quota ──────────────────────────────────────────────────────────────

@router.get("/quota")
def get_quota():
    try:
        with open(QUOTA_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"remaining": None, "used": None, "last": None, "updated_at": None}


# ─── /api/jobs ───────────────────────────────────────────────────────────────

def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


def _read_schedule() -> dict:
    try:
        with open(SCHEDULE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


_SCHEDULE_KEY_MAP = {
    "run_backup_job":          "backup",
    "run_settlement_job":      "settlement",
    "run_continuous_job":      "continuous",
    "run_agent_recalibration": "recalibration",
    "run_calendar_refresh":    "calendar_refresh",
}


@router.get("/jobs")
def get_scheduled_jobs():
    from datetime import timedelta

    now = datetime.now(tz=timezone.utc)
    today = now.date()

    schedule = _read_schedule()
    actual: dict[str, str] = {}
    for k, v in _SCHEDULE_KEY_MAP.items():
        if k not in schedule:
            continue
        try:
            dt = datetime.fromisoformat(schedule[k])
            if dt > now:
                actual[v] = schedule[k]
        except (ValueError, TypeError):
            pass

    backup_hour           = _env_int("BACKUP_HOUR", 4)
    morning_hour          = _env_int("MORNING_HOUR", 8)
    run_interval_hours    = _env_int("RUN_INTERVAL_HOURS", 4)
    max_analysis_lead     = _env_int("MAX_ANALYSIS_LEAD_HOURS", 6)
    calendar_refresh_hour = _env_int("CALENDAR_REFRESH_HOUR", 20)
    recalibration_hour    = (calendar_refresh_hour - 1) % 24

    def _next_daily(hour: int) -> str:
        from datetime import timedelta
        candidate = datetime(today.year, today.month, today.day, hour, 0, 0, tzinfo=timezone.utc)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate.isoformat()

    def _next_interval(interval_hours: int) -> str:
        return (now + timedelta(hours=interval_hours)).isoformat()

    def _next_weekly_sun(hour: int) -> str:
        days_ahead = (6 - today.weekday()) % 7
        if days_ahead == 0:
            candidate = datetime(today.year, today.month, today.day, hour, 0, 0, tzinfo=timezone.utc)
            if candidate <= now:
                candidate += timedelta(weeks=1)
        else:
            next_sun = today + timedelta(days=days_ahead)
            candidate = datetime(next_sun.year, next_sun.month, next_sun.day, hour, 0, 0, tzinfo=timezone.utc)
        return candidate.isoformat()

    return [
        {"id": "backup",           "label": "Backup",              "schedule": f"Daily {backup_hour:02d}:00 UTC",                                           "next_run": actual.get("backup",           _next_daily(backup_hour))},
        {"id": "settlement",       "label": "Settlement",          "schedule": f"Daily {morning_hour:02d}:00 UTC",                                          "next_run": actual.get("settlement",       _next_daily(morning_hour))},
        {"id": "continuous",       "label": "Snapshot + Analysis", "schedule": f"Every {run_interval_hours}h (analysis window: {max_analysis_lead}h)",       "next_run": actual.get("continuous",       _next_interval(run_interval_hours))},
        {"id": "recalibration",    "label": "Agent Recalibration", "schedule": f"Sun {recalibration_hour:02d}:00 UTC",                                      "next_run": actual.get("recalibration",    _next_weekly_sun(recalibration_hour))},
        {"id": "calendar_refresh", "label": "Calendar Refresh",    "schedule": f"Sun {calendar_refresh_hour:02d}:00 UTC",                                   "next_run": actual.get("calendar_refresh", _next_weekly_sun(calendar_refresh_hour))},
    ]
