import tokens from '../../tokens';
import Header from './Header';
import Sidebar from './Sidebar';

export default function Shell({ children, page, setPage, mode, profiles, activeProfile, switchProfile, switching, sidebarData }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {mode === 'live' && (
        <div style={{
          background: tokens.colors.redDim,
          border: `1px solid ${tokens.colors.red}`,
          padding: '6px 24px',
          fontSize: tokens.fontSize.sm,
          color: tokens.colors.red,
          textAlign: 'center',
          letterSpacing: '.1em',
          flexShrink: 0,
        }}>
          ⚠ LIVE MODE ACTIVE — Real stakes will be placed
        </div>
      )}
      <Header mode={mode} profiles={profiles} activeProfile={activeProfile} switchProfile={switchProfile} switching={switching} />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar page={page} setPage={setPage} mode={mode} activeProfile={activeProfile} sidebarData={sidebarData} />
        <div style={{ flex: 1, padding: tokens.spacing.xl, overflowY: 'auto' }}>
          {children}
        </div>
      </div>
    </div>
  );
}
