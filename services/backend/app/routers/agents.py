from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.database import get_db, get_rw_db, rows_to_dicts, resolve_profile_id

router = APIRouter()


@router.get("")
def get_agents(profile: Optional[str] = Query(None)):
    try:
        with get_db() as conn:
            pid = resolve_profile_id(conn, profile)
            if pid:
                agents = rows_to_dicts(conn.execute(
                    "SELECT * FROM agent_states WHERE profile_id = ? ORDER BY id", (pid,)
                ).fetchall())
            else:
                agents = rows_to_dicts(conn.execute(
                    "SELECT * FROM agent_states ORDER BY id"
                ).fetchall())

            for a in agents:
                a["agent_id"] = a.pop("id", a.get("agent_id"))
                aid = a["agent_id"]
                q = (
                    "SELECT COUNT(*) total,"
                    "       SUM(outcome='won') won,"
                    "       SUM(outcome='lost') lost,"
                    "       SUM(outcome IS NULL) pending,"
                    "       AVG(CASE WHEN clv IS NOT NULL THEN clv END) clv_avg"
                    " FROM agent_picks WHERE agent_id=?"
                )
                p: list = [aid]
                if pid:
                    q += " AND profile_id=?"
                    p.append(pid)
                s = conn.execute(q, p).fetchone()
                settled = (s["won"] or 0) + (s["lost"] or 0)
                a.update({
                    "total_picks": s["total"] or 0,
                    "won":         s["won"] or 0,
                    "lost":        s["lost"] or 0,
                    "pending":     s["pending"] or 0,
                    "clv_avg":     round(s["clv_avg"], 2) if s["clv_avg"] else 0,
                    "win_rate":    round(s["won"] / settled * 100, 1) if settled else 0,
                })
            return agents
    except Exception:
        return []


@router.post("/{agent_id}/decommission")
def decommission_agent(agent_id: str, profile: Optional[str] = Query(None)):
    with get_rw_db() as conn:
        pid = profile or (
            conn.execute("SELECT id FROM profiles WHERE is_active = 1 LIMIT 1").fetchone() or {}
        ).get("id")
        if not pid:
            raise HTTPException(400, detail="No profile specified or active")
        agent = conn.execute(
            "SELECT * FROM agent_states WHERE id = ? AND profile_id = ?", (agent_id, pid)
        ).fetchone()
        if not agent:
            raise HTTPException(404, detail="Agent not found")
        if agent["decommissioned_at"]:
            raise HTTPException(400, detail="Agent already decommissioned")
        now = datetime.now(tz=timezone.utc).isoformat()
        conn.execute(
            "UPDATE agent_states SET decommissioned_at = ? WHERE id = ? AND profile_id = ?",
            (now, agent_id, pid),
        )
        conn.commit()
    return {"agent_id": agent_id, "profile_id": pid, "decommissioned_at": now}


@router.post("/{agent_id}/recommission")
def recommission_agent(agent_id: str, profile: Optional[str] = Query(None)):
    with get_rw_db() as conn:
        pid = profile or (
            conn.execute("SELECT id FROM profiles WHERE is_active = 1 LIMIT 1").fetchone() or {}
        ).get("id")
        if not pid:
            raise HTTPException(400, detail="No profile specified or active")
        agent = conn.execute(
            "SELECT * FROM agent_states WHERE id = ? AND profile_id = ?", (agent_id, pid)
        ).fetchone()
        if not agent:
            raise HTTPException(404, detail="Agent not found")
        if not agent["decommissioned_at"]:
            raise HTTPException(400, detail="Agent is not decommissioned")
        conn.execute(
            "UPDATE agent_states SET decommissioned_at = NULL WHERE id = ? AND profile_id = ?",
            (agent_id, pid),
        )
        conn.commit()
    return {"agent_id": agent_id, "profile_id": pid, "decommissioned_at": None}
