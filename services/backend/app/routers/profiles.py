import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.database import get_db, get_rw_db, rows_to_dicts

router = APIRouter()

_AGENT_IDS = list("ABCDE")


def _validate_agents(agents_cfg: list) -> None:
    for i, a in enumerate(agents_cfg):
        aid = _AGENT_IDS[i]
        if not isinstance(a.get("bankroll"), (int, float)) or a["bankroll"] <= 0:
            raise HTTPException(400, detail=f"Agent {aid}: bankroll must be a positive number")
        if not 0.30 <= a.get("confidence_threshold", 0) <= 0.90:
            raise HTTPException(400, detail=f"Agent {aid}: confidence_threshold must be 0.30–0.90")
        if a.get("staking_strategy") not in ("flat", "kelly"):
            raise HTTPException(400, detail=f"Agent {aid}: staking_strategy must be flat or kelly")
        sw = a.get("statistical_weight", 0.7)
        mw = a.get("market_weight", 0.3)
        if not (0 < sw <= 1 and 0 < mw <= 1):
            raise HTTPException(400, detail=f"Agent {aid}: weights must be between 0 and 1")


@router.get("")
def list_profiles():
    try:
        with get_db() as conn:
            return rows_to_dicts(conn.execute("SELECT * FROM profiles ORDER BY created_at ASC").fetchall())
    except Exception:
        return []


@router.post("")
async def create_profile(request: Request):
    body = await request.json()
    name         = body.get("name")
    profile_type = body.get("type", "paper")
    agents_cfg   = body.get("agents", [])

    if not name:
        raise HTTPException(400, detail="name is required")
    if profile_type not in ("paper", "live", "backtest"):
        raise HTTPException(400, detail="type must be paper, live, or backtest")
    if not agents_cfg or len(agents_cfg) > 5:
        raise HTTPException(400, detail="agents must be an array of 1–5 items")

    _validate_agents(agents_cfg)

    profile_id     = str(uuid.uuid4())
    now            = datetime.now(tz=timezone.utc).isoformat()
    bankroll_start = sum(a["bankroll"] for a in agents_cfg)

    with get_rw_db() as conn:
        conn.execute(
            "INSERT INTO profiles (id, name, type, bankroll_start, is_active, created_at)"
            " VALUES (?, ?, ?, ?, 0, ?)",
            (profile_id, name, profile_type, bankroll_start, now),
        )
        for i, a in enumerate(agents_cfg):
            conn.execute(
                """INSERT INTO agent_states
                   (id, statistical_weight, market_weight, confidence_threshold,
                    staking_strategy, kelly_fraction, learning_rate, update_count,
                    bankroll, starting_bankroll, total_picks, total_settled,
                    created_at, last_updated_at, profile_id)
                   VALUES (?, ?, ?, ?, ?, ?, 0.01, 0, ?, ?, 0, 0, ?, ?, ?)""",
                (
                    _AGENT_IDS[i],
                    a.get("statistical_weight", 0.7),
                    a.get("market_weight", 0.3),
                    a["confidence_threshold"],
                    a["staking_strategy"],
                    a.get("kelly_fraction", 0.25),
                    a["bankroll"], a["bankroll"],
                    now, now, profile_id,
                ),
            )
        conn.commit()

    return {"id": profile_id, "name": name, "type": profile_type,
            "bankroll_start": bankroll_start, "is_active": False, "created_at": now}


@router.get("/{profile_id}")
def get_profile(profile_id: str):
    try:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
            if not row:
                raise HTTPException(404, detail="Profile not found")
            return dict(row)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(500, detail="Failed to read profile")


@router.patch("/{profile_id}")
async def update_profile(profile_id: str, request: Request):
    body = await request.json()
    with get_rw_db() as conn:
        existing = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        if not existing:
            raise HTTPException(404, detail="Profile not found")
        name = body.get("name", existing["name"])
        conn.execute("UPDATE profiles SET name = ? WHERE id = ?", (name, profile_id))
        conn.commit()
        return dict(conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone())


@router.delete("/{profile_id}")
def delete_profile(profile_id: str):
    with get_rw_db() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        if not row:
            raise HTTPException(404, detail="Profile not found")
        if row["is_active"]:
            raise HTTPException(400, detail="Cannot delete the active profile")
        conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        conn.commit()
    return {"deleted": True}


@router.post("/{profile_id}/activate")
def activate_profile(profile_id: str):
    with get_rw_db() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        if not row:
            raise HTTPException(404, detail="Profile not found")
        new_val = 0 if row["is_active"] else 1
        conn.execute("UPDATE profiles SET is_active = ? WHERE id = ?", (new_val, profile_id))
        conn.commit()
        return dict(conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone())
