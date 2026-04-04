# Mobile UI — End-to-End Implementation Plan

## Overview

The desktop app is unchanged. A second Vite entry point compiles into `dist/mobile/`
and is served by the existing FastAPI backend at `/mobile`. All data hooks, API
endpoints, and primitive components are shared. Only layouts and page components are
new.

---

## 1. Repository changes

```
services/frontend/
  mobile/
    index.html          ← second Vite HTML entry (mirrors frontend/index.html)
  src/
    mobile/
      MobileApp.jsx     ← root component, profile context, bottom-nav routing
      pages/
        MobileOverviewPage.jsx
        MobilePicksFeedPage.jsx
        MobilePnLPage.jsx
        MobileFixturesPage.jsx
        MobileAgentsPage.jsx
        MobileLogsPage.jsx
      components/
        BottomNav.jsx   ← 5-tab bar pinned to bottom
        MobileShell.jsx ← wraps page content above the nav bar
    mobile.jsx          ← Vite entry point (analogous to main.jsx)
```

Everything under `src/api/`, `src/hooks/`, `src/components/primitives/`, and
`src/tokens.js` is imported as-is — no duplication.

---

## 2. Vite config change (`vite.config.js`)

Add a second input to the rollup build. Vite natively supports this via
`rollupOptions.input`:

```js
build: {
  rollupOptions: {
    input: {
      main:   'index.html',
      mobile: 'mobile/index.html',
    }
  }
}
```

Both apps build into `dist/`. The desktop app lands at `dist/index.html` as before.
The mobile app lands at `dist/mobile/index.html`.

---

## 3. Backend change (`services/backend/main.py`)

The existing catch-all SPA handler is extended with a 4-line path split:

```python
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    static_root = STATIC_DIR.resolve()
    try:
        target = (static_root / full_path).resolve()
        target.relative_to(static_root)
    except (ValueError, Exception):
        raise HTTPException(status_code=404)

    if target.is_file():
        mime, _ = mimetypes.guess_type(str(target))
        return FileResponse(str(target), media_type=mime or "application/octet-stream")

    # Route /mobile/* to mobile SPA, everything else to desktop SPA
    is_mobile_route = full_path == "mobile" or full_path.startswith("mobile/")
    spa_index = static_root / ("mobile/index.html" if is_mobile_route else "index.html")
    if spa_index.is_file():
        return FileResponse(str(spa_index), media_type="text/html",
                            headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    raise HTTPException(status_code=404)
```

Result:
- `http://host:8080/`               → desktop
- `http://host:8080/mobile`         → mobile
- `http://host:8080/mobile#picks`   → mobile, picks tab active

---

## 4. Mobile entry point (`src/mobile.jsx`)

Mirrors `src/main.jsx` exactly, but mounts `<MobileApp />` instead of `<App />`:

```jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import MobileApp from './mobile/MobileApp'

createRoot(document.getElementById('root')).render(
  <StrictMode><MobileApp /></StrictMode>
)
```

---

## 5. `mobile/index.html`

Copy of `frontend/index.html` with the script src pointing at `../src/mobile.jsx`
and a `<meta name="viewport">` tag (critical for mobile rendering):

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
```

---

## 6. `MobileApp.jsx`

Owns profile state (reuses `useProfiles` hook), page state via `#hash`, and passes
`profileId` down to each page. Renders `<MobileShell>` wrapping the active page.

Navigation tabs (5 items — the most useful on mobile):

| Tab | Icon | Desktop equivalent |
|---|---|---|
| Overview | ◈ | OverviewPage |
| Picks | ◎ | PicksFeedPage |
| P&L | ▲ | PnLPage |
| Fixtures | ▦ | FixturesPage |
| Agents | ⬡ | AgentsPage |

Logs, Profiles, and System are omitted from bottom-nav (rarely needed on mobile).
They can be added as an overflow sheet later if required.

---

## 7. `MobileShell.jsx`

A thin wrapper that:
- Sets `min-height: 100dvh` (dynamic viewport height — handles mobile browser chrome)
- Adds `padding-bottom: 64px` so page content is never obscured by the bottom nav
- Applies `overscroll-behavior: none` to prevent pull-to-refresh on iOS

```
┌──────────────────────────────┐
│  scrollable page content      │
│  (padding-bottom: 64px)       │
│                               │
│                               │
├──────────────────────────────┤
│  BottomNav (fixed, 56px tall) │
└──────────────────────────────┘
```

---

## 8. `BottomNav.jsx`

Fixed to the bottom, full width, `56px` tall. 5 icon+label cells. Active tab gets
the mode-colour underline (same green/amber logic as desktop sidebar). Uses
`env(safe-area-inset-bottom)` to pad correctly on iPhone notch devices.

---

## 9. Mobile pages — detailed design

### `MobileOverviewPage.jsx`

**What it shows:** Bankroll, Net P&L, Win Rate, and Today's Fixtures stats — then
a compact agent list — then the 6 most recent picks.

**How it's built:**
- The 4 metric cards are laid out in a `2×2` grid instead of `4×1`. Each card is
  ~50% viewport width. The sparkline and coloured top-bar from the desktop version
  are kept.
- Agent cards become a vertical list (1 per row). Each shows: agent letter, bankroll,
  P&L badge, threshold, win rate, and a miniature `WeightBar`. The 3-column inner
  grid from the desktop is collapsed to 2 columns (bankroll + picks | win rate +
  threshold).
- Recent Picks is an expandable section: shows 3 rows by default, "Show all" links
  to the Picks tab.
- Scheduler status dot is kept in a small inline strip at the top (running/stopped).

**Data:** Reuses `fetchStatus`, `fetchAgents`, `fetchPicks`, `fetchFixtures` with
the same intervals as the desktop.

---

### `MobilePicksFeedPage.jsx`

**What it shows:** Status summary strip (Total / Won / Lost / Pending / Net P&L),
filter chips, then one card per pick (not a table).

**How it's built:**
- The desktop `5-column stat grid` becomes a horizontal scrolling chip strip showing
  the 5 figures inline.
- Filter tabs (all / won / lost / pending) become horizontally scrollable pill chips.
- Each pick is rendered as a `Card`:
  ```
  ┌──────────────────────────────────────┐
  │ [A]  Man Utd v Arsenal    [WON ✓]    │
  │ PL · HOME_WIN · 2.10 · £10.00        │
  │ Conf 74.2%  P&L +£12.10  CLV +3.1%  │
  └──────────────────────────────────────┘
  ```
  First row: AgentTag, match name, outcome Badge.  
  Second row: league, selection, odds, stake (muted, small).  
  Third row: confidence, P&L (green/red), CLV (green/red).

**Why cards instead of table:** The desktop table has 10 columns — impossible to
read on 390px. Cards let each field breathe while keeping all data visible.

---

### `MobilePnLPage.jsx`

**What it shows:** 4 summary metrics, the cumulative P&L bar chart, and per-agent
breakdown cards.

**How it's built:**
- The `4-column metric row` becomes a `2×2` grid.
- The cumulative P&L bar chart from the desktop is kept exactly — it already
  scales well vertically. The only change is setting `height: 120px` instead of
  `160px` to preserve viewport space.
- Per-agent cards become a single-column list. Each card is more compact than
  the desktop:
  ```
  ┌──────────────────────────────────────┐
  │ Agent A              [+£24.50 ↑]     │
  │ ROI +4.1%  Win Rate 58%              │
  │ CLV +2.3%  13W / 8L / 3P            │
  └──────────────────────────────────────┘
  ```
  The 4-column `per-agent` desktop grid is replaced with 2 rows of 2 key-value
  pairs per card.

---

### `MobileFixturesPage.jsx`

**What it shows:** Date picker, league filter chips, and a vertical list of fixtures.

**How it's built:**
- The `3-column stat cards` (Fixtures, Filtered, Leagues) are dropped — the counts
  appear inline in the header text: "14 fixtures · 2 Leagues".
- Date controls: ← / date input / → / Today — kept as-is, they're already compact.
- League chips become a horizontally scrollable row (no wrapping).
- Each fixture is a compact row (no table):
  ```
  ┌──────────────────────────────────────┐
  │ 3:00 PM   Man Utd  vs  Arsenal       │
  │           Premier League             │
  └──────────────────────────────────────┘
  ```
  Kickoff time on the left, teams in the centre, league below in muted text.
  A thin border-left coloured by league (cycling through a set of palette colours)
  adds visual grouping.

---

### `MobileAgentsPage.jsx`

**What it shows:** One card per agent with full stats and the decommission toggle.

**How it's built:**
- The desktop `2-column card grid` becomes single-column.
- Inside each card the `3×2 stat grid` is kept but uses `2×3` instead (two columns,
  three rows) which fits a mobile viewport.
- The `WeightBar` is kept — it's already a thin horizontal element.
- The Decommission / Recommission action is a full-width button at the card bottom
  with a 44px tap target (WCAG minimum), not a small text link.
- Decommissioned agents are visually dimmed (opacity 0.45) as on desktop.

---

### `MobileLogsPage.jsx`

**What it shows:** Level filter chips, poll picker, and the scrollable log list.

**How it's built:**
- Level chips (ALL / INFO / WARN / ERROR) and interval picker (30s / 1m / 5m / 15m)
  are placed on two separate `flex-wrap: wrap` rows so they don't overflow.
- The log list is rendered as a `<pre>`-style mono block capped at `calc(100dvh - 180px)`,
  same auto-scroll behaviour as the desktop.
- Each log line is one line of text: `[LEVEL] timestamp message`. Level badges are
  simple colour-coded prefixes.
- This page is accessed via a "Logs" entry in a sheet/drawer triggered from an overflow
  button (⋮) in the mobile header, since it's lower priority.

---

## 10. Optional: User-agent redirect

Add a small inline script inside the desktop `index.html` that nudges phone users:

```html
<script>
  const mobile = /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent);
  if (mobile && !window.location.pathname.startsWith('/mobile')) {
    window.location.replace('/mobile' + window.location.hash);
  }
</script>
```

This is optional and reversible. Does not affect desktop browsers.

---

## 11. Build & deploy

No Docker changes are needed. The existing `Dockerfile.dashboard` runs `npm run build`
which now emits both `dist/index.html` and `dist/mobile/index.html`. The FastAPI
backend serves both from the same `./static` directory.

Build verification:

```bash
cd services/frontend
npm run build
# Expect:
#   dist/index.html
#   dist/assets/main-*.js
#   dist/mobile/index.html
#   dist/assets/mobile-*.js
```

---

## 12. Implementation order

| Step | What | Risk |
|------|------|------|
| 1 | `vite.config.js` — add mobile input | Low — additive only |
| 2 | `mobile/index.html` + `src/mobile.jsx` | Low |
| 3 | `MobileShell.jsx` + `BottomNav.jsx` | Low |
| 4 | `MobileApp.jsx` (routing skeleton) | Low |
| 5 | `MobileOverviewPage.jsx` | Medium — most complex page |
| 6 | `MobilePicksFeedPage.jsx` | Medium |
| 7 | `MobilePnLPage.jsx` | Low |
| 8 | `MobileFixturesPage.jsx` | Low |
| 9 | `MobileAgentsPage.jsx` | Low |
| 10 | `MobileLogsPage.jsx` | Low |
| 11 | Backend catch-all update | Low — 4-line change |
| 12 | Optional UA redirect in `index.html` | Low |
