from typing import Optional

from fastapi import APIRouter, Query

from app.database import get_db_for_profile, rows_to_dicts

router = APIRouter()


@router.get("")
def get_picks(
    status:  Optional[str] = Query(None),
    agent:   Optional[str] = Query(None),
    profile: Optional[str] = Query(None),
    date:    Optional[str] = Query(None),
    limit:   int           = Query(200, ge=1, le=1000),
):
    try:
        with get_db_for_profile(profile) as (conn, pid):
            q = "SELECT * FROM agent_picks WHERE 1=1"
            p: list = []
            if pid:
                q += " AND profile_id=?"; p.append(pid)
            if status:
                if status == "pending":
                    q += " AND outcome IS NULL"
                else:
                    q += " AND outcome=?"; p.append(status)
            if agent:
                q += " AND agent_id=?"; p.append(agent)
            if date:
                q += " AND DATE(recorded_at)=?"; p.append(date)
            q += " ORDER BY recorded_at DESC LIMIT ?"; p.append(limit)
            return rows_to_dicts(conn.execute(q, p).fetchall())
    except Exception:
        return []
