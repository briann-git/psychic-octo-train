import tokens from '../../tokens';

export default function MobileShell({ children }) {
  return (
    <div style={{
      minHeight: '100dvh',
      background: tokens.colors.bg,
      color: tokens.colors.text,
      fontFamily: tokens.fonts.mono,
      fontSize: 13,
      display: 'flex',
      flexDirection: 'column',
      overscrollBehavior: 'none',
    }}>
      {/* scrollable content area — bottom padding leaves room for the nav bar */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        overflowX: 'hidden',
        paddingBottom: 'calc(56px + env(safe-area-inset-bottom))',
        WebkitOverflowScrolling: 'touch',
      }}>
        {children}
      </div>
    </div>
  );
}
