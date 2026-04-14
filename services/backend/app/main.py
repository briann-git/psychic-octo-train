from fastapi import FastAPI

from app.routers import agents, backtest, config, fixtures, logs, picks, pnl, profiles, status

app = FastAPI(title="Pipeline Ops API", version="2.0.0")

app.include_router(status.router,   prefix="/api")
app.include_router(profiles.router, prefix="/api/profiles")
app.include_router(agents.router,   prefix="/api/agents")
app.include_router(picks.router,    prefix="/api/picks")
app.include_router(pnl.router,      prefix="/api/pnl")
app.include_router(fixtures.router, prefix="/api/fixtures")
app.include_router(logs.router,     prefix="/api/logs")
app.include_router(config.router,   prefix="/api/config")
app.include_router(backtest.router, prefix="/api/backtest")
