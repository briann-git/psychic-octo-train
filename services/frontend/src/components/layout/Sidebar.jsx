import tokens from '../../tokens';

const NAV = [
  { id: 'overview',  icon: '◈', label: 'Overview' },
  { id: 'picks',     icon: '◎', label: 'Picks Feed' },
  { id: 'pnl',       icon: '▲', label: 'P&L' },
  { id: 'agents',    icon: '⬡', label: 'Agents' },
  { id: 'fixtures',  icon: '▦', label: 'Fixtures' },
  { id: 'logs',      icon: '≡', label: 'Logs' },
  { id: 'settings',  icon: '⚙', label: 'Settings' },
];

export default function Sidebar({ page, setPage, mode, sidebarData }) {
  const modeColor = mode === 'paper' ? tokens.colors.amber : tokens.colors.green;
  const modeDim   = mode === 'paper' ? tokens.colors.amberDim : tokens.colors.greenDim;
  const { netPnl = null, totalPicks = null, quotaUsed = null, quotaTotal = null } = sidebarData || {};

  return (
    <div style={{
      width: 220,
      borderRight: `1px solid ${tokens.colors.border}`,
      flexShrink: 0,
      overflowY: 'auto',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{ padding: '20px 16px 8px' }}>
        <div style={{ fontSize: tokens.fontSize.sm, letterSpacing: '.2em', textTransform: 'uppercase', color: tokens.colors.muted, marginBottom: tokens.spacing.sm, padding: '0 8px' }}>
          View
        </div>
        {NAV.map(item => (
          <div
            key={item.id}
            onClick={() => setPage(item.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '8px 10px', cursor: 'pointer',
              color: page === item.id ? modeColor : tokens.colors.muted,
              background: page === item.id ? modeDim : 'transparent',
              border: `1px solid ${page === item.id ? modeColor : 'transparent'}`,
              marginBottom: 2, transition: 'all .15s', fontSize: tokens.fontSize.base,
            }}
          >
            <span style={{ width: 14, textAlign: 'center', fontSize: 13 }}>{item.icon}</span>
            <span>{item.label}</span>
          </div>
        ))}
      </div>

      <div style={{ padding: tokens.spacing.lg, borderTop: `1px solid ${tokens.colors.border}`, marginTop: 'auto' }}>
        <div style={{ fontSize: tokens.fontSize.sm, letterSpacing: '.15em', textTransform: 'uppercase', color: tokens.colors.muted, marginBottom: 10 }}>
          {mode === 'paper' ? 'Paper Trading' : 'Live Trading'}
        </div>

        {[
          { label: 'Total Picks', value: totalPicks !== null ? String(totalPicks) : '—', color: modeColor },
          { label: 'Net P&L', value: netPnl !== null ? `${netPnl >= 0 ? '+' : ''}£${(+netPnl).toFixed(2)}` : '—', color: netPnl >= 0 ? tokens.colors.green : tokens.colors.red },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ padding: 10, border: `1px solid ${tokens.colors.border}`, background: tokens.colors.surface, marginBottom: 6 }}>
            <div style={{ fontSize: tokens.fontSize.xs, color: tokens.colors.muted, letterSpacing: '.1em', textTransform: 'uppercase', marginBottom: 4 }}>{label}</div>
            <div style={{ fontSize: 16, fontWeight: 500, color }}>{value}</div>
          </div>
        ))}

        {quotaTotal && (
          <div style={{ padding: 10, border: `1px solid ${tokens.colors.border}`, background: tokens.colors.surface, marginTop: 4 }}>
            <div style={{ fontSize: tokens.fontSize.xs, color: tokens.colors.muted, letterSpacing: '.1em', textTransform: 'uppercase', marginBottom: 6 }}>Odds API</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: tokens.fontSize.base, marginBottom: 6 }}>
              <span>{quotaUsed}</span>
              <span style={{ color: tokens.colors.muted }}>/ {quotaTotal}</span>
            </div>
            <div style={{ height: 4, background: tokens.colors.border }}>
              <div style={{ height: '100%', width: `${Math.min((quotaUsed / quotaTotal) * 100, 100)}%`, background: tokens.colors.amber }} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
