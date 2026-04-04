import tokens from '../../tokens';
import PRESETS, { defaultAgent } from './presets';
import AgentCard from './AgentCard';

const PRESET_KEYS = ['conservative', 'balanced', 'aggressive', 'custom'];

export default function StepAgents({ agents, onAgentsChange, preset, onPresetChange }) {
  const selectPreset = (key) => {
    onPresetChange(key);
    onAgentsChange(PRESETS[key].agents.map(a => ({ ...a })));
  };

  const updateAgent = (index, agent) => {
    const next = [...agents];
    next[index] = agent;
    onAgentsChange(next);
  };

  const total = agents.reduce((s, a) => s + (a.bankroll || 0), 0);

  return (
    <div>
      {/* Preset picker */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: tokens.colors.muted, marginBottom: 6 }}>
          Start from a template
        </label>
        <div style={{ display: 'flex', gap: 6 }}>
          {PRESET_KEYS.map(key => {
            const p = PRESETS[key];
            const active = preset === key;
            return (
              <div
                key={key}
                onClick={() => selectPreset(key)}
                style={{
                  flex: 1, padding: '8px 6px', textAlign: 'center', cursor: 'pointer',
                  border: `1px solid ${active ? tokens.colors.green : tokens.colors.border}`,
                  background: active ? tokens.colors.greenDim : tokens.colors.surface2,
                  transition: 'all .15s',
                }}
              >
                <div style={{ fontSize: 11, fontWeight: 600, color: active ? tokens.colors.green : tokens.colors.text, marginBottom: 2 }}>
                  {p.label}
                </div>
                <div style={{ fontSize: 10, color: tokens.colors.muted }}>{p.description}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Agent count selector */}
      <div style={{ marginBottom: 12 }}>
        <label style={{ display: 'block', fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: tokens.colors.muted, marginBottom: 6 }}>
          Number of agents
        </label>
        <div style={{ display: 'flex', gap: 0 }}>
          {[1, 2, 3, 4, 5].map(n => {
            const active = agents.length === n;
            return (
              <div
                key={n}
                onClick={() => {
                  if (n === agents.length) return;
                  onPresetChange('custom');
                  if (n > agents.length) {
                    const extras = Array.from({ length: n - agents.length }, () => defaultAgent());
                    onAgentsChange([...agents, ...extras]);
                  } else {
                    onAgentsChange(agents.slice(0, n));
                  }
                }}
                style={{
                  flex: 1, padding: '8px 0', textAlign: 'center',
                  fontSize: 13, fontWeight: 600, cursor: 'pointer',
                  border: `1px solid ${active ? tokens.colors.green : tokens.colors.border}`,
                  background: active ? tokens.colors.greenDim : tokens.colors.surface2,
                  color: active ? tokens.colors.green : tokens.colors.muted,
                  transition: 'all .15s',
                }}
              >{n}</div>
            );
          })}
        </div>
      </div>

      {/* Agent cards */}
      <div style={{ maxHeight: 340, overflowY: 'auto' }}>
        {agents.map((agent, i) => (
          <AgentCard key={i} index={i} agent={agent} onChange={a => updateAgent(i, a)} />
        ))}
      </div>

      {/* Total bankroll */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', padding: '10px 0',
        borderTop: `1px solid ${tokens.colors.border}`, marginTop: 8,
        fontSize: 12, color: tokens.colors.muted,
      }}>
        <span style={{ letterSpacing: '.1em', textTransform: 'uppercase' }}>Total bankroll</span>
        <span style={{ fontFamily: tokens.fonts.mono, color: tokens.colors.text }}>£{total.toLocaleString()}</span>
      </div>
    </div>
  );
}
