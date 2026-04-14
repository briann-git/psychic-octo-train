import { useState, useCallback, useEffect } from 'react';
import Shell from './components/layout/Shell';
import OverviewPage  from './pages/OverviewPage';
import PicksFeedPage from './pages/PicksFeedPage';
import PnLPage       from './pages/PnLPage';
import AgentsPage    from './pages/AgentsPage';
import FixturesPage  from './pages/FixturesPage';
import LogsPage      from './pages/LogsPage';
import ProfilesPage  from './pages/ProfilesPage';
import SystemPage    from './pages/SystemPage';
import BacktestsPage from './pages/BacktestsPage';
import useProfiles from './hooks/useProfiles';
import useApi from './hooks/useApi';
import { fetchPnl } from './api/endpoints';

const PAGES = {
  overview:  OverviewPage,
  picks:     PicksFeedPage,
  pnl:       PnLPage,
  agents:    AgentsPage,
  fixtures:  FixturesPage,
  logs:      LogsPage,
  profiles:  ProfilesPage,
  backtests: BacktestsPage,
  system:    SystemPage,
};

function getInitialPage() {
  const hash = window.location.hash.replace('#', '');
  return PAGES[hash] ? hash : 'overview';
}

export default function App() {
  const [page, setPageState] = useState(getInitialPage);
  const {
    profiles, viewedProfile, mode, loading,
    selectProfile, toggleActive, createProfile, removeProfile, reload: reloadProfiles,
  } = useProfiles();

  const profileId = viewedProfile ? viewedProfile.id : null;

  const setPage = useCallback((p) => {
    setPageState(p);
    window.location.hash = p;
  }, []);

  useEffect(() => {
    const onHash = () => {
      const hash = window.location.hash.replace('#', '');
      if (PAGES[hash]) setPageState(hash);
    };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  // Sidebar summary data from PnL endpoint — scoped to active profile
  const pnlFetcher = useCallback(() => fetchPnl(profileId), [profileId]);
  const { data: pnlData } = useApi(pnlFetcher, { interval: 60000 });
  const sidebarData = {
    netPnl:    pnlData ? pnlData.agents.reduce((s, a) => s + (a.net_pnl || 0), 0) : null,
    totalPicks: pnlData ? pnlData.agents.reduce((s, a) => s + (a.total_picks || 0), 0) : null,
  };

  const PageComponent = PAGES[page] || OverviewPage;

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: '#555', fontFamily: 'IBM Plex Mono, monospace', fontSize: 12 }}>
        Loading…
      </div>
    );
  }

  return (
    <Shell
      page={page}
      setPage={setPage}
      mode={mode}
      profiles={profiles}
      viewedProfile={viewedProfile}
      selectProfile={selectProfile}
      sidebarData={sidebarData}
    >
      <PageComponent
        mode={mode}
        profileId={profileId}
        profiles={profiles}
        viewedProfile={viewedProfile}
        selectProfile={selectProfile}
        toggleActive={toggleActive}
        createProfile={createProfile}
        removeProfile={removeProfile}
        reloadProfiles={reloadProfiles}
        setPage={setPage}
      />
    </Shell>
  );
}
