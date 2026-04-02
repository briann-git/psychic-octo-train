import tokens from '../../tokens';

const AGENT_IDS = ['A', 'B', 'C', 'D', 'E'];

const TYPE_COLORS = {
  paper: tokens.colors.amber,
  live: tokens.colors.green,
  backtest: tokens.colors.blue,
};

export default function StepReview({ name, type, agents }) {
  const total = agents.reduce((s, a) => s + (a.bankroll || 0), 0);
  const tc = TYPE_COLORS[type] || tokens.colors.amber;

  const th = { padding: '6px 8px', fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', color: tokens.colors.muted, textAlign: 'left', borderBottom: `1px solid ${tokens.colors.border}` };
  const td = { padding: '6px 8px', fontSize: 12, fontFamily: tokens.fonts.mono, color: tokens.colors.text, borderBottom: `1px solid ${tokens.colors.border}` };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <span style={{ fontSize: 14, fontWeight: 600, color: tokens.colors.text }}>{name || 'Unnamed'}</span>
        <span style={{
          fontSize: 10, letterSpacing: '.15em', textTransform: 'uppercase',
          padding: '3px 8px', border: `1px solid ${tc}`, color: tc,
        }}>{type}</span>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 12 }}>
        <thead>
          <tr>
            <th style={th}>Agent</th>
            <th style={th}>Bankroll</th>
            <th style={th}>Conf</th>
            <th style={th}>Staking</th>
            <th style={th}>Stat / Mkt</th>
          </tr>
        </thead>
        <tbody>
          {agents.map((a, i) => (
            <tr key={i}>
              <td style={td}>{AGENT_IDS[i]}</td>
              <td style={td}>£{a.bankroll}</td>
              <td style={td}>{a.confidence_threshold.toFixed(2)}</td>
              <td style={td}>
                {a.staking_strategy === 'kelly' ? `Kelly ${a.kelly_fraction.toFixed(2)}` : 'Flat'}
              </td>
              <td style={td}>
                {Math.round(a.statistical_weight * 100)}/{Math.round(a.market_weight * 100)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{
        display: 'flex', justifyContent: 'space-between', padding: '8px 0',
        fontSize: 12, color: tokens.colors.muted,
      }}>
        <span style={{ letterSpacing: '.1em', textTransform: 'uppercase' }}>Total bankroll</span>
        <span style={{ fontFamily: tokens.fonts.mono, color: tokens.colors.text, fontWeight: 600 }}>£{total.toLocaleString()}</span>
      </div>

      {type === 'live' && (
        <div style={{ marginTop: 10, padding: 10, border: `1px solid ${tokens.colors.red}`, background: tokens.colors.redDim, fontSize: 11, color: tokens.colors.red, lineHeight: 1.7 }}>
          ⚠ This will create a live profile. Real stakes will be placed when activated.
        </div>
      )}
    </div>
  );
}
