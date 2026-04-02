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

  const addAgent = () => {
    if (agents.length >= 5) return;
    onPresetChange('custom');
    onAgentsChange([...agents, defaultAgent()]);
  };

  const removeAgent = () => {
    if (agents.length <= 1) return;
    onPresetChange('custom');
    onAgentsChange(agents.slice(0, -1));
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

      {/* Agent count controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
        <span style={{ fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase', color: tokens.colors.muted }}>
          Agents ({agents.length})
        </span>
        <div style={{ display: 'flex', gap: 6 }}>
          <div
            onClick={removeAgent}
            style={{
              padding: '3px 10px', fontSize: 11, cursor: agents.length <= 1 ? 'not-allowed' : 'pointer',
              border: `1px solid ${tokens.colors.border}`, background: tokens.colors.surface2,
              color: agents.length <= 1 ? tokens.colors.dim : tokens.colors.text,
              opacity: agents.length <= 1 ? 0.4 : 1,
            }}
          >− Remove</div>
          <div
            onClick={addAgent}
            style={{
              padding: '3px 10px', fontSize: 11, cursor: agents.length >= 5 ? 'not-allowed' : 'pointer',
              border: `1px solid ${tokens.colors.green}`, background: tokens.colors.greenDim,
              color: agents.length >= 5 ? tokens.colors.dim : tokens.colors.green,
              opacity: agents.length >= 5 ? 0.4 : 1,
            }}
          >+ Add</div>
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
