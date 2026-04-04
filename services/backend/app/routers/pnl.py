from typing import Optional

from fastapi import APIRouter, Query

from app.database import get_db_for_profile

router = APIRouter()


@router.get("")
def get_pnl(profile: Optional[str] = Query(None)):
    result: dict = {"agents": [], "daily_series": []}
    try:
        with get_db_for_profile(profile) as (conn, pid):

            agent_q = "SELECT DISTINCT agent_id FROM agent_picks"
            agent_p: list = []
            if pid:
                agent_q += " WHERE profile_id=?"; agent_p.append(pid)
            agent_q += " ORDER BY agent_id"

            for a in conn.execute(agent_q, agent_p).fetchall():
                aid = a["agent_id"]
                q = """
                    SELECT COUNT(*) total,
                           SUM(outcome='won') won,
                           SUM(outcome='lost') lost,
                           SUM(outcome IS NULL) pending,
                           COALESCE(SUM(pnl),0) net_pnl,
                           AVG(CASE WHEN clv IS NOT NULL THEN clv END) clv_avg,
                           COALESCE(SUM(stake),0) staked
                    FROM agent_picks WHERE agent_id=?
                """
                p: list = [aid]
                if pid:
                    q += " AND profile_id=?"; p.append(pid)
                s = conn.execute(q, p).fetchone()
                settled = (s["won"] or 0) + (s["lost"] or 0)
                result["agents"].append({
                    "agent_id":    aid,
                    "total_picks": s["total"] or 0,
                    "won":         s["won"] or 0,
                    "lost":        s["lost"] or 0,
                    "pending":     s["pending"] or 0,
                    "net_pnl":     round(s["net_pnl"], 2),
                    "clv_avg":     round(s["clv_avg"], 2) if s["clv_avg"] else 0,
                    "win_rate":    round(s["won"] / settled * 100, 1) if settled else 0,
                    "roi":         round(s["net_pnl"] / s["staked"] * 100, 2) if s["staked"] else 0,
                })

            daily_q = """
                SELECT DATE(settled_at) date, SUM(pnl) dpnl
                FROM agent_picks WHERE settled_at IS NOT NULL AND pnl IS NOT NULL
            """
            daily_p: list = []
            if pid:
                daily_q += " AND profile_id=?"; daily_p.append(pid)
            daily_q += " GROUP BY DATE(settled_at) ORDER BY date"

            cumulative = 0.0
            for row in conn.execute(daily_q, daily_p).fetchall():
                cumulative += row["dpnl"]
                result["daily_series"].append({
                    "date":           row["date"],
                    "daily_pnl":      round(row["dpnl"], 2),
                    "cumulative_pnl": round(cumulative, 2),
                })
    except Exception:
        pass
    return result
