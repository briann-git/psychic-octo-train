import asyncio
import json
import os
import re
import sqlite3
import mimetypes
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse

# ─── Config ──────────────────────────────────────────────────────────────────

_API_KEY_RE = re.compile(r'(apiKey=)[^&\s]+', re.IGNORECASE)

DB_PATH = os.environ.get("DB_PATH", "/data/db/ledger.db")
LOG_DIR = os.environ.get("LOG_DIR", "/data/logs")
LOG_FILE = os.path.join(LOG_DIR, "scheduler.log")
HEARTBEAT_DIR = os.environ.get("HEARTBEAT_DIR", "/data/heartbeat")
HEARTBEAT_FILE = os.path.join(HEARTBEAT_DIR, "scheduler.json")
HEARTBEAT_STALE_SECONDS = 15 * 60  # 15 minutes — heartbeat is every 10 min
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Pipeline Ops Dashboard", version="1.0.0")

# ─── DB ──────────────────────────────────────────────────────────────────────

@contextmanager
def get_db():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def rows_to_dicts(rows):
    return [dict(r) for r in rows]

# ─── Heartbeat ───────────────────────────────────────────────────────────────

def _read_heartbeat() -> dict | None:
    """Read the scheduler heartbeat file. Returns None if missing or unreadable."""
    try:
        with open(HEARTBEAT_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _is_scheduler_running() -> bool:
    """True if heartbeat was received within the staleness window."""
    hb = _read_heartbeat()
    if not hb or "timestamp" not in hb:
        return False
    try:
        ts = datetime.fromisoformat(hb["timestamp"])
        age = (datetime.now(tz=timezone.utc) - ts).total_seconds()
        return age < HEARTBEAT_STALE_SECONDS
    except (ValueError, TypeError):
        return False

# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/api/status")
def get_status():
    heartbeat = _read_heartbeat()
    running = _is_scheduler_running()
    result = {
        "scheduler_running": running,
        "last_run": None,
        "uptime": heartbeat.get("timestamp") if heartbeat else None,
        "db_size": None,
    }

    if os.path.exists(DB_PATH):
        sz = os.path.getsize(DB_PATH)
        result["db_size"] = f"{sz / (1024 * 1024):.1f} MB"

    try:
        with get_db() as conn:
            row = conn.execute("SELECT MAX(recorded_at) AS lr FROM agent_picks").fetchone()
            if row and row["lr"]:
                result["last_run"] = row["lr"]
    except Exception:
        pass

    return result


@app.get("/api/agents")
def get_agents():
    try:
        with get_db() as conn:
            agents = rows_to_dicts(conn.execute("SELECT * FROM agent_states ORDER BY id").fetchall())
            for a in agents:
                a["agent_id"] = a.pop("id", a.get("agent_id"))
                aid = a["agent_id"]
                s = conn.execute("""
                    SELECT COUNT(*) total,
                           SUM(outcome='won') won,
                           SUM(outcome='lost') lost,
                           SUM(outcome IS NULL) pending,
                           AVG(CASE WHEN clv IS NOT NULL THEN clv END) clv_avg
                    FROM agent_picks WHERE agent_id=?
                """, (aid,)).fetchone()
                a["total_picks"] = s["total"] or 0
                a["won"] = s["won"] or 0
                a["lost"] = s["lost"] or 0
                a["pending"] = s["pending"] or 0
                a["clv_avg"] = round(s["clv_avg"], 2) if s["clv_avg"] else 0
                settled = (s["won"] or 0) + (s["lost"] or 0)
                a["win_rate"] = round(s["won"] / settled * 100, 1) if settled else 0
            return agents
    except Exception:
        return []


@app.get("/api/picks")
def get_picks(
    status: Optional[str] = Query(None),
    agent: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    try:
        with get_db() as conn:
            q = "SELECT * FROM agent_picks WHERE 1=1"
            p: list = []
            if status:
                if status == "pending":
                    q += " AND outcome IS NULL"
                else:
                    q += " AND outcome=?"
                    p.append(status)
            if agent:
                q += " AND agent_id=?"
                p.append(agent)
            q += " ORDER BY recorded_at DESC LIMIT ?"
            p.append(limit)
            return rows_to_dicts(conn.execute(q, p).fetchall())
    except Exception:
        return []


@app.get("/api/pnl")
def get_pnl():
    result: dict = {"agents": [], "daily_series": []}
    try:
        with get_db() as conn:
            for a in conn.execute("SELECT DISTINCT agent_id FROM agent_picks ORDER BY agent_id").fetchall():
                aid = a["agent_id"]
                s = conn.execute("""
                    SELECT COUNT(*) total,
                           SUM(outcome='won') won,
                           SUM(outcome='lost') lost,
                           SUM(outcome IS NULL) pending,
                           COALESCE(SUM(pnl),0) net_pnl,
                           AVG(CASE WHEN clv IS NOT NULL THEN clv END) clv_avg,
                           COALESCE(SUM(stake),0) staked
                    FROM agent_picks WHERE agent_id=?
                """, (aid,)).fetchone()
                settled = (s["won"] or 0) + (s["lost"] or 0)
                result["agents"].append({
                    "agent_id": aid,
                    "total_picks": s["total"] or 0,
                    "won": s["won"] or 0,
                    "lost": s["lost"] or 0,
                    "pending": s["pending"] or 0,
                    "net_pnl": round(s["net_pnl"], 2),
                    "clv_avg": round(s["clv_avg"], 2) if s["clv_avg"] else 0,
                    "win_rate": round(s["won"] / settled * 100, 1) if settled else 0,
                    "roi": round(s["net_pnl"] / s["staked"] * 100, 2) if s["staked"] else 0,
                })
            cumulative = 0.0
            for row in conn.execute("""
                SELECT DATE(settled_at) date, SUM(pnl) dpnl
                FROM agent_picks WHERE settled_at IS NOT NULL AND pnl IS NOT NULL
                GROUP BY DATE(settled_at) ORDER BY date
            """).fetchall():
                cumulative += row["dpnl"]
                result["daily_series"].append({
                    "date": row["date"],
                    "daily_pnl": round(row["dpnl"], 2),
                    "cumulative_pnl": round(cumulative, 2),
                })
    except Exception:
        pass
    return result


@app.get("/api/fixtures")
def get_fixtures(
    league: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
):
    try:
        with get_db() as conn:
            q = "SELECT * FROM fixture_calendar WHERE 1=1"
            p: list = []
            if league:
                q += " AND league=?"; p.append(league)
            if date:
                q += " AND DATE(kickoff)=?"; p.append(date)
            q += " ORDER BY kickoff"
            rows = rows_to_dicts(conn.execute(q, p).fetchall())
            for r in rows:
                r["home"] = r.pop("home_team", "")
                r["away"] = r.pop("away_team", "")
            return rows
    except Exception:
        return []


# ─── Log file helpers ────────────────────────────────────────────────────────

_LOG_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s+"
    r"\[(\w+)\]\s+(\S+)\s+[—\-–]\s+(.*)"
)


def _parse_log_line(line: str) -> dict | None:
    m = _LOG_RE.match(line)
    if m:
        return {
            "time": m.group(1),
            "level": m.group(2),
            "source": m.group(3),
            "message": _API_KEY_RE.sub(r'\1REDACTED', m.group(4)),
        }
    return None


def _tail_log_file(path: str, limit: int) -> list[str]:
    """
    Read the last *limit* complete lines from *path*.

    Race-condition safe: opens read-only and tolerates the writer appending
    or RotatingFileHandler rotating underneath us.  If the file is truncated
    mid-read we simply return what we got.
    """
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return []
    try:
        try:
            size = os.fstat(fd).st_size
        except OSError:
            return []
        if size == 0:
            return []

        # Read a generous chunk from the end.  4 KB per line is very
        # conservative; real lines are ~200 bytes.
        chunk_size = min(size, limit * 4096)
        try:
            os.lseek(fd, max(size - chunk_size, 0), os.SEEK_SET)
            raw = os.read(fd, chunk_size)
        except OSError:
            return []

        text = raw.decode("utf-8", errors="replace")
        lines = text.split("\n")

        # The first element may be a partial line if we seeked mid-line;
        # drop it unless we read from the start of the file.
        if size > chunk_size:
            lines = lines[1:]

        # Strip empty trailing element from the final newline
        if lines and not lines[-1]:
            lines.pop()

        return lines[-limit:]
    finally:
        os.close(fd)


@app.get("/api/logs")
def get_logs(
    level: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    raw_lines = _tail_log_file(LOG_FILE, limit * 2)
    entries: list[dict] = []
    for line in raw_lines:
        entry = _parse_log_line(line)
        if entry is None:
            continue
        if level and entry["level"] != level.upper():
            continue
        entries.append(entry)
    return entries[-limit:]


@app.get("/api/logs/stream")
async def stream_logs():
    """
    SSE endpoint that tails the log file.

    Opens the file read-only and polls for new data every second.
    If RotatingFileHandler rotates the file (inode changes or file
    shrinks) we re-open transparently.
    """
    async def generator():
        fd: int | None = None
        inode: int = 0
        pos: int = 0

        def _open() -> tuple[int, int, int]:
            """Open log file, return (fd, inode, size)."""
            f = os.open(LOG_FILE, os.O_RDONLY)
            stat = os.fstat(f)
            return f, stat.st_ino, stat.st_size

        try:
            while True:
                # (re-)open if necessary
                if fd is None:
                    try:
                        fd, inode, size = _open()
                        pos = size  # skip existing content, only stream new
                    except OSError:
                        await asyncio.sleep(2)
                        continue

                # Check for rotation: new inode or file got smaller
                try:
                    cur_stat = os.stat(LOG_FILE)
                except OSError:
                    # File temporarily missing during rotation
                    os.close(fd)
                    fd = None
                    await asyncio.sleep(1)
                    continue

                if cur_stat.st_ino != inode or cur_stat.st_size < pos:
                    os.close(fd)
                    try:
                        fd, inode, size = _open()
                        pos = 0  # rotated — read from start
                    except OSError:
                        fd = None
                        await asyncio.sleep(1)
                        continue

                # Read new bytes
                try:
                    os.lseek(fd, pos, os.SEEK_SET)
                    raw = os.read(fd, 65536)
                except OSError:
                    os.close(fd)
                    fd = None
                    await asyncio.sleep(1)
                    continue

                if raw:
                    text = raw.decode("utf-8", errors="replace")
                    pos += len(raw)
                    for line in text.split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        entry = _parse_log_line(line)
                        if entry:
                            yield f"data: {json.dumps(entry)}\n\n"

                await asyncio.sleep(1)
        finally:
            if fd is not None:
                os.close(fd)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


_SAFE_KEYS = {
    "PAPER_TRADING", "DB_PATH", "CONFIDENCE_THRESHOLD", "FLAT_STAKE",
    "MIN_LEAD_HOURS", "MAX_LEAD_HOURS", "LOG_LEVEL",
    "BACKUP_HOUR", "MORNING_HOUR", "SNAPSHOT_HOUR", "ANALYSIS_HOUR",
    "CALENDAR_LOOKAHEAD_DAYS", "CALENDAR_REFRESH_HOUR",
    "BETTING_LEAGUES_CONFIG", "BETTING_MARKETS_CONFIG",
    "CSV_CACHE_DIR", "CSV_MAX_AGE_HOURS",
}


@app.get("/api/config")
def get_config():
    cfg = {k: os.environ[k] for k in _SAFE_KEYS if k in os.environ}
    cfg.setdefault("PAPER_TRADING", "true")
    return cfg


@app.patch("/api/config")
async def update_config(request: Request):
    body = await request.json()
    updated: dict = {}
    for key, value in body.items():
        if key not in _SAFE_KEYS:
            raise HTTPException(status_code=400, detail=f"Unknown config key: {key}")
        os.environ[key] = str(value)
        updated[key] = str(value)
    return updated


# ─── SPA static serving ──────────────────────────────────────────────────────

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    # Prevent path traversal
    static_root = STATIC_DIR.resolve()
    try:
        target = (static_root / full_path).resolve()
        target.relative_to(static_root)
    except (ValueError, Exception):
        raise HTTPException(status_code=404)

    if target.is_file():
        mime, _ = mimetypes.guess_type(str(target))
        return FileResponse(str(target), media_type=mime or "application/octet-stream")

    index = static_root / "index.html"
    if index.is_file():
        return FileResponse(
            str(index),
            media_type="text/html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    raise HTTPException(status_code=404)
