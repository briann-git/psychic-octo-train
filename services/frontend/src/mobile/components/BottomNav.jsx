import tokens from '../../tokens';

const NAV = [
  { id: 'overview',  icon: '◈', label: 'Overview'  },
  { id: 'picks',     icon: '◎', label: 'Picks'      },
  { id: 'pnl',       icon: '▲', label: 'P&L'        },
  { id: 'fixtures',  icon: '▦', label: 'Fixtures'   },
  { id: 'agents',    icon: '⬡', label: 'Agents'     },
];

export default function BottomNav({ page, setPage, mode }) {
  const activeColor = mode === 'live' ? tokens.colors.green
    : mode === 'backtest' ? '#67e8f9'
    : tokens.colors.amber;

  return (
    <div style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      height: 'calc(56px + env(safe-area-inset-bottom))',
      paddingBottom: 'env(safe-area-inset-bottom)',
      background: tokens.colors.surface,
      borderTop: `1px solid ${tokens.colors.border}`,
      display: 'flex',
      alignItems: 'stretch',
      zIndex: 100,
    }}>
      {NAV.map(({ id, icon, label }) => {
        const active = page === id;
        return (
          <button
            key={id}
            onClick={() => setPage(id)}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 3,
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              borderTop: `2px solid ${active ? activeColor : 'transparent'}`,
              color: active ? activeColor : tokens.colors.dim,
              padding: '6px 0 0',
              transition: 'color .15s',
              WebkitTapHighlightColor: 'transparent',
              /* minimum 44px tap target */
              minHeight: 44,
            }}
          >
            <span style={{ fontSize: 16, lineHeight: 1 }}>{icon}</span>
            <span style={{ fontSize: 9, letterSpacing: '.1em', textTransform: 'uppercase' }}>{label}</span>
          </button>
        );
      })}
    </div>
  );
}
