import { useState, useCallback, useEffect } from 'react';
import tokens from '../tokens';
import useProfiles from '../hooks/useProfiles';
import MobileShell from './components/MobileShell';
import BottomNav from './components/BottomNav';
import ProfileSwitcher from './components/ProfileSwitcher';
import MobileOverviewPage from './pages/MobileOverviewPage';
import MobilePicksFeedPage from './pages/MobilePicksFeedPage';
import MobilePnLPage from './pages/MobilePnLPage';
import MobileFixturesPage from './pages/MobileFixturesPage';
import MobileAgentsPage from './pages/MobileAgentsPage';
import MobileLogsPage from './pages/MobileLogsPage';

const PAGES = {
  overview: MobileOverviewPage,
  picks:    MobilePicksFeedPage,
  pnl:      MobilePnLPage,
  fixtures: MobileFixturesPage,
  agents:   MobileAgentsPage,
  logs:     MobileLogsPage,
};

function getInitialPage() {
  const hash = window.location.hash.replace('#', '');
  return PAGES[hash] ? hash : 'overview';
}

export default function MobileApp() {
  const [page, setPageState] = useState(getInitialPage);
  const [switcherOpen, setSwitcherOpen] = useState(false);
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

  const PageComponent = PAGES[page] || MobileOverviewPage;

  if (loading) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100dvh', color: tokens.colors.dim,
        fontFamily: tokens.fonts.mono, fontSize: 12,
        background: tokens.colors.bg,
      }}>
        Loading…
      </div>
    );
  }

  return (
    <MobileShell>
      {/* Page header strip */}
      <div style={{
        padding: '12px 16px 8px',
        borderBottom: `1px solid ${tokens.colors.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        background: tokens.colors.bg,
        zIndex: 50,
      }}>
        <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '.2em', textTransform: 'uppercase', color: tokens.colors.text }}>
          Pipeline Ops
        </span>
        {viewedProfile && (
          <span
            onClick={() => setSwitcherOpen(true)}
            style={{
              fontSize: 9, letterSpacing: '.12em', textTransform: 'uppercase',
              padding: '2px 7px',
              border: `1px solid ${mode === 'live' ? tokens.colors.green : mode === 'backtest' ? '#67e8f9' : tokens.colors.amber}`,
              color: mode === 'live' ? tokens.colors.green : mode === 'backtest' ? '#67e8f9' : tokens.colors.amber,
              cursor: 'pointer',
              WebkitTapHighlightColor: 'transparent',
            }}>
            {viewedProfile.name} · {mode} ▾
          </span>
        )}
      </div>

      {/* Active page */}
      <div style={{ padding: '16px 12px 0' }}>
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
        />
      </div>

      <BottomNav page={page} setPage={setPage} mode={mode} />

      <ProfileSwitcher
        open={switcherOpen}
        onClose={() => setSwitcherOpen(false)}
        profiles={profiles}
        viewedProfile={viewedProfile}
        selectProfile={selectProfile}
      />
    </MobileShell>
  );
}
