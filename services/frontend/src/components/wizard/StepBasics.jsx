import tokens from '../../tokens';

const TYPES = [
  { value: 'paper', label: 'Paper', color: tokens.colors.amber, bg: tokens.colors.amberDim },
  { value: 'live', label: 'Live', color: tokens.colors.green, bg: tokens.colors.greenDim },
  { value: 'backtest', label: 'Backtest', color: tokens.colors.blue, bg: tokens.colors.blueDim },
];

export default function StepBasics({ name, type, onNameChange, onTypeChange }) {
  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: tokens.colors.muted, marginBottom: 6 }}>
          Profile Name
        </label>
        <input
          value={name}
          onChange={e => onNameChange(e.target.value)}
          placeholder="e.g. Conservative Paper"
          autoFocus
          style={{
            width: '100%', padding: '8px 10px', fontSize: 13,
            background: tokens.colors.surface2, border: `1px solid ${tokens.colors.border}`,
            color: tokens.colors.text, outline: 'none', boxSizing: 'border-box',
          }}
        />
      </div>

      <div>
        <label style={{ display: 'block', fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: tokens.colors.muted, marginBottom: 6 }}>
          Type
        </label>
        <div style={{ display: 'flex', gap: 0 }}>
          {TYPES.map(t => {
            const active = t.value === type;
            return (
              <div
                key={t.value}
                onClick={() => onTypeChange(t.value)}
                style={{
                  flex: 1, padding: '10px 0', textAlign: 'center',
                  fontSize: 11, letterSpacing: '.15em', textTransform: 'uppercase',
                  cursor: 'pointer',
                  background: active ? t.bg : tokens.colors.surface2,
                  border: `1px solid ${active ? t.color : tokens.colors.border2}`,
                  color: active ? t.color : tokens.colors.muted,
                  transition: 'all .15s',
                }}
              >
                {t.label}
              </div>
            );
          })}
        </div>

        {type === 'live' && (
          <div style={{ marginTop: 10, padding: 10, border: `1px solid ${tokens.colors.red}`, background: tokens.colors.redDim, fontSize: 11, color: tokens.colors.red, lineHeight: 1.7 }}>
            ⚠ Live mode places real stakes. Ensure bookmaker keys and bankroll limits are configured.
          </div>
        )}
      </div>
    </div>
  );
}
