from typing import Optional

from fastapi import APIRouter, Query

from app.database import get_db, rows_to_dicts

router = APIRouter()


@router.get("")
def get_fixtures(
    league: Optional[str] = Query(None),
    date:   Optional[str] = Query(None),
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
