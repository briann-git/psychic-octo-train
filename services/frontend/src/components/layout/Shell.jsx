import tokens from '../../tokens';
import Header from './Header';
import Sidebar from './Sidebar';

export default function Shell({ children, page, setPage, mode, profiles, viewedProfile, selectProfile, sidebarData }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <Header mode={mode} profiles={profiles} viewedProfile={viewedProfile} selectProfile={selectProfile} />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar page={page} setPage={setPage} mode={mode} viewedProfile={viewedProfile} sidebarData={sidebarData} />
        <div style={{ flex: 1, padding: tokens.spacing.xl, overflowY: 'auto' }}>
          {children}
        </div>
      </div>
    </div>
  );
}
