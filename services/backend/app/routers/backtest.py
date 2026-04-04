import json
import sqlite3
import uuid
from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.config import BACKTEST_DB_PATH, DB_PATH
from app.database import get_db, get_rw_db

router = APIRouter()


def _parse_dt(val: str | None, field_name: str) -> "datetime | None":
    if not val:
        return None
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid date format for {field_name!r}: {val!r}")


def _serialise_result(result_dict: dict) -> dict:
    """Normalise datetime objects to ISO strings inside a result dict."""
    for point in result_dict.get("equity_curve", []):
        if isinstance(point.get("fixture_date"), datetime):
            point["fixture_date"] = point["fixture_date"].isoformat()
    cfg = result_dict.get("config", {})
    for key in ("date_from", "date_to"):
        if isinstance(cfg.get(key), datetime):
            cfg[key] = cfg[key].isoformat()
    return result_dict


# ── Run ───────────────────────────────────────────────────────────────────────

@router.post("/run")
async def run_backtest(request: Request):
    """
    POST /api/backtest/run
    Body: { "profile_id", "league", "season", "date_from"?, "date_to"? }
    Any profile type may be backtested. Results are persisted as a report.
    """
    body = await request.json()

    profile_id = body.get("profile_id")
    league = body.get("league")
    season = body.get("season")

    if not profile_id or not league or not season:
        raise HTTPException(status_code=400, detail="profile_id, league, and season are required")

    with get_db() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    date_from = _parse_dt(body.get("date_from"), "date_from")
    date_to   = _parse_dt(body.get("date_to"),   "date_to")

    try:
        from betting.adapters.football_data import FootballDataProvider
        from betting.adapters.odds_api import OddsApiProvider
        from betting.adapters.sqlite_ledger import SqliteLedgerRepository
        from betting.config import settings as betting_settings
        from betting.config.league_config import LeagueConfigLoader
        from betting.config.market_config import MarketConfigLoader
        from betting.models.backtest import BacktestConfig
        from betting.services.agent_repository import AgentRepository
        from betting.services.backtest_runner import BacktestRunner
        from betting.services.csv_download_service import CsvDownloadService

        league_loader = LeagueConfigLoader()
        market_loader = MarketConfigLoader()

        odds_api = OddsApiProvider(
            api_key=betting_settings.odds_api_key,
            league_loader=league_loader,
            market_loader=market_loader,
        )
        csv_service = CsvDownloadService(
            cache_dir=betting_settings.csv_cache_dir,
            max_age_hours=betting_settings.csv_max_age_hours,
            league_loader=league_loader,
        )
        stats_provider = FootballDataProvider(
            csv_service=csv_service,
            league_loader=league_loader,
        )

        # backtest.db is ephemeral scratch space — wipe per-profile data before each run
        # Copy the profile's real agents from ledger.db into backtest.db at their
        # starting bankroll so the backtest uses exactly the configured agents.
        live_conn = sqlite3.connect(DB_PATH, timeout=10)
        live_conn.row_factory = sqlite3.Row
        try:
            live_agents = live_conn.execute(
                "SELECT * FROM agent_states WHERE profile_id = ? AND decommissioned_at IS NULL",
                (profile_id,),
            ).fetchall()
        finally:
            live_conn.close()

        bt_conn2 = sqlite3.connect(BACKTEST_DB_PATH, timeout=10)
        bt_conn2.row_factory = sqlite3.Row
        try:
            # Tables with profile_id: filter by profile
            for tbl in ("picks", "skips", "agent_picks", "agent_states"):
                bt_conn2.execute(f"DELETE FROM {tbl} WHERE profile_id = ?", (profile_id,))
            # Tables without profile_id: wipe entirely (scratch data)
            bt_conn2.execute("DELETE FROM pick_signals")
            bt_conn2.execute("DELETE FROM odds_history")
            bt_conn2.execute(
                "INSERT OR IGNORE INTO profiles (id, name, type, bankroll_start, is_active, created_at) VALUES (?,?,?,?,?,?)",
                (row["id"], row["name"], row["type"], row["bankroll_start"], 0, row["created_at"]),
            )
            # Seed backtest.db with the profile's configured agents, reset to starting bankroll
            for a in live_agents:
                d = dict(a)
                d["bankroll"] = row["bankroll_start"]
                d["starting_bankroll"] = row["bankroll_start"]
                d["update_count"] = 0
                d["total_picks"] = 0
                d["total_settled"] = 0
                cols = list(d.keys())
                placeholders = ",".join("?" * len(cols))
                bt_conn2.execute(
                    f"INSERT OR REPLACE INTO agent_states ({','.join(cols)}) VALUES ({placeholders})",
                    [d[c] for c in cols],
                )
            bt_conn2.commit()
        finally:
            bt_conn2.close()

        backtest_ledger = SqliteLedgerRepository(db_path=BACKTEST_DB_PATH, flat_stake=betting_settings.flat_stake)
        backtest_agent_repo = AgentRepository(db_path=BACKTEST_DB_PATH)
        # Agents are already seeded above; bootstrap_agents is a no-op when agents exist

        runner = BacktestRunner(
            config=BacktestConfig(league=league, season=season, date_from=date_from, date_to=date_to),
            profile_id=profile_id,
            odds_api=odds_api,
            csv_service=csv_service,
            stats_provider=stats_provider,
            ledger_repo=backtest_ledger,
            agent_repo=backtest_agent_repo,
            league_loader=league_loader,
            market_loader=market_loader,
            agent_weights=betting_settings.agent_weights,
            confidence_threshold=betting_settings.confidence_threshold,
            flat_stake=betting_settings.flat_stake,
        )

        result = runner.run()
        result_dict = _serialise_result(asdict(result))

        # Compute per-agent and per-market breakdowns from scratch DB
        bt_conn3 = sqlite3.connect(BACKTEST_DB_PATH, timeout=10)
        bt_conn3.row_factory = sqlite3.Row
        try:
            by_agent = []
            for r in bt_conn3.execute(
                """SELECT agent_id,
                          COUNT(*) AS picks,
                          SUM(CASE WHEN outcome='won' THEN 1 ELSE 0 END) AS won,
                          SUM(CASE WHEN outcome='lost' THEN 1 ELSE 0 END) AS lost,
                          SUM(stake) AS total_staked,
                          SUM(pnl) AS net_pnl,
                          AVG(CASE WHEN clv IS NOT NULL THEN clv END) AS clv_avg
                   FROM agent_picks
                   WHERE outcome IS NOT NULL AND profile_id = ?
                   GROUP BY agent_id
                   ORDER BY agent_id""",
                (profile_id,),
            ).fetchall():
                d = dict(r)
                d["roi"] = (d["net_pnl"] / d["total_staked"]) if d["total_staked"] else 0
                d["win_rate"] = round((d["won"] / d["picks"] * 100), 1) if d["picks"] else 0
                by_agent.append(d)

            by_market = []
            for r in bt_conn3.execute(
                """SELECT market,
                          COUNT(*) AS picks,
                          SUM(CASE WHEN outcome='won' THEN 1 ELSE 0 END) AS won,
                          SUM(CASE WHEN outcome='lost' THEN 1 ELSE 0 END) AS lost,
                          SUM(stake) AS total_staked,
                          SUM(CASE WHEN outcome='won' THEN (stake * (odds - 1))
                                   WHEN outcome='lost' THEN -stake
                                   ELSE 0 END) AS net_pnl
                   FROM picks
                   WHERE outcome IS NOT NULL AND profile_id = ?
                   GROUP BY market
                   ORDER BY picks DESC""",
                (profile_id,),
            ).fetchall():
                d = dict(r)
                d["roi"] = (d["net_pnl"] / d["total_staked"]) if d["total_staked"] else 0
                d["win_rate"] = round((d["won"] / d["picks"] * 100), 1) if d["picks"] else 0
                by_market.append(d)

            result_dict["pnl_summary"]["by_agent"] = by_agent
            result_dict["pnl_summary"]["by_market"] = by_market
        finally:
            bt_conn3.close()

        # Persist the report in ledger.db
        report_id = str(uuid.uuid4())
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        with get_rw_db() as rw:
            rw.execute(
                """INSERT INTO backtest_reports
                   (id, profile_id, league, season, date_from, date_to,
                    fixtures_processed, picks_made, equity_curve, pnl_summary, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    report_id,
                    profile_id,
                    league,
                    season,
                    result_dict["config"].get("date_from"),
                    result_dict["config"].get("date_to"),
                    result_dict["fixtures_processed"],
                    result_dict["picks_made"],
                    json.dumps(result_dict["equity_curve"]),
                    json.dumps(result_dict["pnl_summary"]),
                    now_iso,
                ),
            )
            rw.commit()

        return {"report_id": report_id, **result_dict}

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backtest run failed: {exc}")


# ── Reports list ──────────────────────────────────────────────────────────────

@router.get("/reports")
async def list_backtest_reports(profile: str | None = None):
    """GET /api/backtest/reports?profile=<id>  — returns list, no equity_curve."""
    with get_db() as conn:
        if profile:
            rows = conn.execute(
                """SELECT id, profile_id, league, season, date_from, date_to,
                          fixtures_processed, picks_made, pnl_summary, created_at
                   FROM backtest_reports WHERE profile_id = ?
                   ORDER BY created_at DESC""",
                (profile,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, profile_id, league, season, date_from, date_to,
                          fixtures_processed, picks_made, pnl_summary, created_at
                   FROM backtest_reports ORDER BY created_at DESC"""
            ).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        d["pnl_summary"] = json.loads(d["pnl_summary"] or "{}")
        result.append(d)
    return result


# ── Single report ─────────────────────────────────────────────────────────────

@router.get("/reports/{report_id}")
async def get_backtest_report(report_id: str):
    """GET /api/backtest/reports/<id>  — includes full equity_curve."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM backtest_reports WHERE id = ?", (report_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    d = dict(row)
    d["equity_curve"] = json.loads(d["equity_curve"] or "[]")
    d["pnl_summary"]  = json.loads(d["pnl_summary"]  or "{}")
    return d


# ── Delete report ─────────────────────────────────────────────────────────────

@router.delete("/reports/{report_id}")
async def delete_backtest_report(report_id: str):
    """DELETE /api/backtest/reports/<id>"""
    with get_rw_db() as conn:
        conn.execute("DELETE FROM backtest_reports WHERE id = ?", (report_id,))
    return {"deleted": report_id}

    """
    POST /api/backtest/run

    Body: {
      "profile_id": "<uuid>",
      "league":     "Premier_League",
      "season":     "2526",
      "date_from":  "2025-08-01T00:00:00Z",   // optional
      "date_to":    "2026-05-31T23:59:59Z"     // optional
    }
    """
    body = await request.json()

    profile_id = body.get("profile_id")
    league = body.get("league")
    season = body.get("season")

    if not profile_id or not league or not season:
        raise HTTPException(status_code=400, detail="profile_id, league, and season are required")

    # Validate profile in the main DB
    with get_db() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    if row["type"] != "backtest":
        raise HTTPException(status_code=400, detail="Profile must be of type 'backtest'")

    date_from = _parse_dt(body.get("date_from"), "date_from")
    date_to = _parse_dt(body.get("date_to"), "date_to")

    try:
        from betting.adapters.football_data import FootballDataProvider
        from betting.adapters.odds_api import OddsApiProvider
        from betting.adapters.sqlite_ledger import SqliteLedgerRepository
        from betting.config import settings as betting_settings
        from betting.config.league_config import LeagueConfigLoader
        from betting.config.market_config import MarketConfigLoader
        from betting.models.backtest import BacktestConfig
        from betting.services.agent_repository import AgentRepository
        from betting.services.backtest_runner import BacktestRunner
        from betting.services.csv_download_service import CsvDownloadService

        league_loader = LeagueConfigLoader()
        market_loader = MarketConfigLoader()

        odds_api = OddsApiProvider(
            api_key=betting_settings.odds_api_key,
            league_loader=league_loader,
            market_loader=market_loader,
        )
        csv_service = CsvDownloadService(
            cache_dir=betting_settings.csv_cache_dir,
            max_age_hours=betting_settings.csv_max_age_hours,
            league_loader=league_loader,
        )
        stats_provider = FootballDataProvider(
            csv_service=csv_service,
            league_loader=league_loader,
        )
        backtest_ledger = SqliteLedgerRepository(
            db_path=BACKTEST_DB_PATH,
            flat_stake=betting_settings.flat_stake,
        )

        # Mirror the profile row into the backtest DB so FK constraints are satisfied
        bt_conn = sqlite3.connect(BACKTEST_DB_PATH, timeout=10)
        bt_conn.row_factory = sqlite3.Row
        try:
            bt_conn.execute(
                """
                INSERT OR IGNORE INTO profiles
                    (id, name, type, bankroll_start, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (row["id"], row["name"], row["type"], row["bankroll_start"], 0, row["created_at"]),
            )
            bt_conn.commit()
        finally:
            bt_conn.close()

        backtest_agent_repo = AgentRepository(db_path=BACKTEST_DB_PATH)
        backtest_agent_repo.bootstrap_agents(
            profile_id=profile_id,
            bankroll_start=row["bankroll_start"],
        )

        runner = BacktestRunner(
            config=BacktestConfig(
                league=league,
                season=season,
                date_from=date_from,
                date_to=date_to,
            ),
            profile_id=profile_id,
            odds_api=odds_api,
            csv_service=csv_service,
            stats_provider=stats_provider,
            ledger_repo=backtest_ledger,
            agent_repo=backtest_agent_repo,
            league_loader=league_loader,
            market_loader=market_loader,
            agent_weights=betting_settings.agent_weights,
            confidence_threshold=betting_settings.confidence_threshold,
            flat_stake=betting_settings.flat_stake,
        )

        result = runner.run()

        result_dict = asdict(result)
        for point in result_dict.get("equity_curve", []):
            if isinstance(point.get("fixture_date"), datetime):
                point["fixture_date"] = point["fixture_date"].isoformat()
        for key in ("date_from", "date_to"):
            cfg_val = result_dict.get("config", {}).get(key)
            if isinstance(cfg_val, datetime):
                result_dict["config"][key] = cfg_val.isoformat()

        return result_dict

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Backtest run failed: {exc}")
