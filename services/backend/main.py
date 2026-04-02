import os
import json
import sqlite3
import mimetypes
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse

# ─── Config ──────────────────────────────────────────────────────────────────

DB_PATH = os.environ.get("DB_PATH", "/data/db/ledger.db")
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

# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/api/status")
def get_status():
    result = {
        "scheduler_running": None,
        "last_run": None,
        "uptime": None,
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
            agents = rows_to_dicts(conn.execute("SELECT * FROM agent_states ORDER BY agent_id").fetchall())
            for a in agents:
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
            return rows_to_dicts(conn.execute(q, p).fetchall())
    except Exception:
        return []


@app.get("/api/logs")
def get_logs(
    level: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    return []


@app.get("/api/logs/stream")
async def stream_logs():
    async def generator():
        yield f"data: {json.dumps({'error': 'log streaming not available'})}\n\n"

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
    try:
        target = (STATIC_DIR / full_path).resolve()
        STATIC_DIR.resolve()
        target.relative_to(STATIC_DIR.resolve())
    except (ValueError, Exception):
        raise HTTPException(status_code=404)

    if target.is_file():
        mime, _ = mimetypes.guess_type(str(target))
        return FileResponse(str(target), media_type=mime or "application/octet-stream")

    index = STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(str(index), media_type="text/html")

    raise HTTPException(status_code=404)
