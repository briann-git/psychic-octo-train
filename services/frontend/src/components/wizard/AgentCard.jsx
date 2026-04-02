import tokens from '../../tokens';

const AGENT_IDS = ['A', 'B', 'C', 'D', 'E'];

function SliderRow({ label, value, min, max, step, format, onChange }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
      <span style={{ width: 80, fontSize: 11, color: tokens.colors.muted, letterSpacing: '.05em' }}>{label}</span>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        style={{ flex: 1, accentColor: tokens.colors.green }}
      />
      <span style={{ width: 52, textAlign: 'right', fontSize: 12, fontFamily: tokens.fonts.mono, color: tokens.colors.text }}>
        {format ? format(value) : value}
      </span>
    </div>
  );
}

export default function AgentCard({ index, agent, onChange }) {
  const update = (field, value) => onChange({ ...agent, [field]: value });

  return (
    <div style={{
      border: `1px solid ${tokens.colors.border}`,
      background: tokens.colors.surface,
      padding: '12px 14px',
      marginBottom: 8,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: tokens.colors.green, letterSpacing: '.15em' }}>
          AGENT {AGENT_IDS[index]}
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
        {/* Bankroll */}
        <div style={{ marginBottom: 8 }}>
          <span style={{ fontSize: 11, color: tokens.colors.muted, letterSpacing: '.05em' }}>Bankroll</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 4 }}>
            <span style={{ fontSize: 12, color: tokens.colors.muted }}>£</span>
            <input
              type="number" min={1} value={agent.bankroll}
              onChange={e => update('bankroll', Math.max(1, parseFloat(e.target.value) || 0))}
              style={{
                width: '100%', padding: '5px 8px', fontSize: 12, fontFamily: tokens.fonts.mono,
                background: tokens.colors.surface2, border: `1px solid ${tokens.colors.border}`,
                color: tokens.colors.text, outline: 'none',
              }}
            />
          </div>
        </div>

        {/* Staking */}
        <div style={{ marginBottom: 8 }}>
          <span style={{ fontSize: 11, color: tokens.colors.muted, letterSpacing: '.05em' }}>Staking</span>
          <select
            value={agent.staking_strategy}
            onChange={e => update('staking_strategy', e.target.value)}
            style={{
              width: '100%', padding: '5px 8px', fontSize: 12, marginTop: 4,
              background: tokens.colors.surface2, border: `1px solid ${tokens.colors.border}`,
              color: tokens.colors.text, outline: 'none',
            }}
          >
            <option value="flat">Flat</option>
            <option value="kelly">Kelly</option>
          </select>
        </div>
      </div>

      <SliderRow
        label="Confidence"
        value={agent.confidence_threshold}
        min={0.50} max={0.90} step={0.01}
        format={v => v.toFixed(2)}
        onChange={v => update('confidence_threshold', v)}
      />

      <SliderRow
        label="Stat / Mkt"
        value={agent.statistical_weight}
        min={0.10} max={0.90} step={0.05}
        format={v => `${Math.round(v * 100)}/${Math.round((1 - v) * 100)}`}
        onChange={v => {
          onChange({ ...agent, statistical_weight: parseFloat(v.toFixed(2)), market_weight: parseFloat((1 - v).toFixed(2)) });
        }}
      />

      {agent.staking_strategy === 'kelly' && (
        <SliderRow
          label="Kelly frac"
          value={agent.kelly_fraction}
          min={0.05} max={0.50} step={0.05}
          format={v => v.toFixed(2)}
          onChange={v => update('kelly_fraction', v)}
        />
      )}
    </div>
  );
}
