# Profile-Based Trading System

## Overview

Profiles provide clean separation between live and paper trading. A **Profile**
is a named, isolated trading context that owns its own agents, bankroll, picks,
and P&L history.

```
┌──────────────────────────────────────────────────────────┐
│                   Shared Resources                       │
│  odds_history · fixture_calendar · CSV cache · configs   │
└──────────────────────────────────────────────────────────┘
        │                       │
  ┌─────┴──────┐         ┌─────┴──────┐
  │  Profile A │         │  Profile B │
  │  (paper)   │         │  (live)    │
  │            │         │            │
  │  Agents    │         │  Agents    │
  │  Picks     │         │  Picks     │
  │  Skips     │         │  Skips     │
  │  P&L       │         │  P&L       │
  └────────────┘         └────────────┘
```

### Profile types

| Type      | Description                                        |
|-----------|----------------------------------------------------|
| `paper`   | Simulated trading – no real money at risk           |
| `live`    | Real trading – bookmaker integration (future)       |
| `backtest`| Historical replay against past data (future)        |

---

## Implementation Phases

### Phase 1 — Data Model & Migration

**Goal**: `Profile` entity + `profile_id` FK on all relevant tables. Existing
data migrates into a default paper profile.

**Files created**:
- `services/betting/models/profile.py`

**Files modified**:
- `services/betting/models/__init__.py`
- `services/betting/adapters/sqlite_ledger.py` (profiles table, migration, profile_id on picks/skips)
- `services/betting/services/agent_repository.py` (profile_id on agent_states/agent_picks)

**Schema changes**:
```sql
-- New table
CREATE TABLE IF NOT EXISTS profiles (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL DEFAULT 'paper',
    bankroll_start REAL NOT NULL DEFAULT 1000.0,
    is_active   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);

-- Altered tables (via migration)
ALTER TABLE picks        ADD COLUMN profile_id TEXT REFERENCES profiles(id);
ALTER TABLE skips        ADD COLUMN profile_id TEXT REFERENCES profiles(id);
ALTER TABLE agent_states ADD COLUMN profile_id TEXT REFERENCES profiles(id);
ALTER TABLE agent_picks  ADD COLUMN profile_id TEXT REFERENCES profiles(id);

-- Default profile + data migration
INSERT INTO profiles VALUES ('default-paper', 'Paper – Default', 'paper', 1000.0, 1, <now>);
UPDATE picks        SET profile_id = 'default-paper' WHERE profile_id IS NULL;
UPDATE skips        SET profile_id = 'default-paper' WHERE profile_id IS NULL;
UPDATE agent_states SET profile_id = 'default-paper' WHERE profile_id IS NULL;
UPDATE agent_picks  SET profile_id = 'default-paper' WHERE profile_id IS NULL;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_picks_profile        ON picks(profile_id);
CREATE INDEX IF NOT EXISTS idx_skips_profile         ON skips(profile_id);
CREATE INDEX IF NOT EXISTS idx_agent_states_profile  ON agent_states(profile_id);
CREATE INDEX IF NOT EXISTS idx_agent_picks_profile   ON agent_picks(profile_id);
```

**Tables left unchanged** (shared resources):
- `odds_history`
- `fixture_calendar`

---

### Phase 2 — Repository Layer

**Goal**: All data access becomes profile-scoped.

**Files created**:
- `services/betting/services/profile_repository.py`

**Files modified**:
- `services/betting/adapters/sqlite_ledger.py` — every query/write gains `profile_id`
- `services/betting/services/agent_repository.py` — every query/write gains `profile_id`

**ProfileRepository methods**:
- `create(profile) → Profile`
- `get(profile_id) → Profile | None`
- `get_active() → Profile | None`
- `list_all() → list[Profile]`
- `set_active(profile_id)`
- `update(profile) → Profile`
- `delete(profile_id)` (guards: cannot delete active or profile with picks)

**SqliteLedger scope changes**:
- `record(state, profile_id)`
- `get_pending_picks(profile_id)`
- `get_all_picks(profile_id)`, `get_all_skips(profile_id)`
- `get_by_fixture(fixture_id, profile_id)`
- Odds/calendar methods: **unchanged**

**AgentRepository scope changes**:
- `bootstrap_agents(profile_id, bankroll_start)`
- `get_all_agents(profile_id)`
- `get_agent(agent_id, profile_id)`
- `save_agent(agent, profile_id)`
- `record_agent_pick(agent_id, pick, profile_id)`
- `get_unsettled_agent_picks(agent_id, profile_id)`
- `get_settled_since(agent_id, since, profile_id)`

---

### Phase 3 — Service Layer

**Goal**: Business logic operates within a profile context.

**Files created**:
- `services/betting/services/profile_service.py`

**Files modified**:
- `services/betting/services/ledger_service.py`
- `services/betting/services/agent_execution_service.py`
- `services/betting/services/agent_recalibration_service.py`
- `services/betting/services/pnl_service.py`
- `services/betting/services/result_ingestion_service.py`
- `services/betting/graph/nodes/ledger.py`

**ProfileService methods**:
- `create_profile(name, type, bankroll_start) → Profile`
- `get_active_profile() → Profile`
- `switch_profile(profile_id)`
- `list_profiles() → list[Profile]`
- `delete_profile(profile_id)`

**Service changes**:

| Service | Change |
|---|---|
| `LedgerService.record(state, profile_id)` | Passes profile_id to repository |
| `AgentExecutionService.__init__(..., profile_id)` | Stores profile_id for all repo calls |
| `AgentRecalibrationService.recalibrate_all(since, profile_id)` | Scopes agent lookup and pick retrieval |
| `PnlService.compute(profile_id)` | Scopes picks and skips queries |
| `ResultIngestionService.settle_pending_picks(leagues, profile_id, season)` | Scopes pending + agent settlement |
| `LedgerNode.__init__(ledger_service, profile_id, profile_type)` | Replaces `paper_trading` bool |

---

### Phase 4 — Scheduler

**Goal**: Scheduler runs against the active profile.

**Files modified**:
- `services/betting/scheduler.py`
- `services/betting/config/__init__.py` (remove `PAPER_TRADING`)

**Changes**:
- `_build_components()` instantiates `ProfileRepository`, resolves active profile
- All jobs receive `profile.id` and pass it through the service stack
- `bootstrap_agents()` is profile-scoped
- `run_analysis()` creates pipeline with `profile.id` and `profile.type`

---

### Phase 5 — Backend API

**Goal**: Profile CRUD + profile-scoped data endpoints.

**Files modified**:
- `services/backend/main.py`

**New endpoints**:

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/profiles` | List all profiles |
| `POST` | `/api/profiles` | Create profile |
| `GET` | `/api/profiles/{id}` | Get profile detail |
| `PATCH` | `/api/profiles/{id}` | Update profile |
| `DELETE` | `/api/profiles/{id}` | Delete profile |
| `POST` | `/api/profiles/{id}/activate` | Set as active |

**Existing endpoint changes**:
- All data endpoints accept `?profile=` (defaults to active)
- `GET /api/status` includes `active_profile` in response
- `GET /api/config` removes `PAPER_TRADING`

---

### Phase 6 — Frontend

**Goal**: Profile switcher replaces paper/live toggle.

**Files created**:
- `services/frontend/src/hooks/useProfiles.js`

**Files deleted**:
- `services/frontend/src/hooks/useTradingMode.js`

**Files modified**:
- `services/frontend/src/api/client.js` (added `post`, `del` helpers)
- `services/frontend/src/api/endpoints.js` (profile CRUD + profile-scoped fetchers)
- `services/frontend/src/App.jsx` (uses `useProfiles`, passes `profileId` to pages)
- `services/frontend/src/components/layout/Shell.jsx` (accepts profile props)
- `services/frontend/src/components/layout/Header.jsx` (profile dropdown replaces toggle)
- `services/frontend/src/components/layout/Sidebar.jsx` (shows active profile name)
- `services/frontend/src/pages/SettingsPage.jsx` (profile management UI)
- `services/frontend/src/pages/OverviewPage.jsx` (accepts `profileId`, scopes fetchers)
- `services/frontend/src/pages/PicksFeedPage.jsx` (accepts `profileId`, scopes fetcher)
- `services/frontend/src/pages/PnLPage.jsx` (accepts `profileId`, scopes fetcher)
- `services/frontend/src/pages/AgentsPage.jsx` (accepts `profileId`, scopes fetcher)

**UI changes**:
- Header: profile dropdown (grouped by type, colour-coded badges)
- Sidebar: accent colour from `profile.type`
- Shell: red banner for live profiles
- Settings: profile management (create/rename/delete)
- All data hooks append `?profile={activeProfileId}` to API calls
