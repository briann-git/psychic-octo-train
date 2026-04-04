import { useState, useCallback } from 'react';
import tokens from '../../tokens';
import Card from '../../components/primitives/Card';
import Badge from '../../components/primitives/Badge';
import WeightBar from '../../components/primitives/WeightBar';
import useApi from '../../hooks/useApi';
import { fetchAgents, decommissionAgent, recommissionAgent } from '../../api/endpoints';

export default function MobileAgentsPage({ profileId }) {
  const { data, loading, refetch } = useApi(
    useCallback(() => fetchAgents(profileId), [profileId]),
    { interval: 30000 }
  );
  const agents = data || [];
  const [busy, setBusy] = useState(null);

  const handleToggle = async (agentId, isDecommissioned) => {
    setBusy(agentId);
    try {
      if (isDecommissioned) {
        await recommissionAgent(agentId, profileId);
      } else {
        await decommissionAgent(agentId, profileId);
      }
      refetch();
    } catch (e) { console.error(e); }
    setBusy(null);
  };

  return (
    <div>
      {loading && <div style={{ color: tokens.colors.muted, fontSize: 12, padding: '8px 0' }}>Loading…</div>}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }} className="fade-in s1">
        {agents.map(a => {
          const pnl   = (a.bankroll || 0) - (a.starting_bankroll || 1000);
          const up    = pnl >= 0;
          const decomm = !!a.decommissioned_at;

          return (
            <Card key={a.agent_id} style={decomm ? { opacity: 0.7, borderColor: tokens.colors.border } : {}}>
              {/* ── Header ── */}
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
                <div>
                  <div style={{ fontSize: 24, fontWeight: 600, marginBottom: 3 }}>Agent {a.agent_id}</div>
                  <div style={{ fontSize: 10, color: tokens.colors.muted, letterSpacing: '.12em', textTransform: 'uppercase' }}>
                    {a.staking_strategy || 'flat'} staking
                    {a.staking_strategy === 'kelly' ? ` · kelly ${a.kelly_fraction}` : ''}
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                  {decomm && (
                    <span style={{ fontSize: 9, letterSpacing: '.1em', textTransform: 'uppercase', padding: '2px 7px', border: `1px solid ${tokens.colors.red}`, color: tokens.colors.red }}>
                      Decommissioned
                    </span>
                  )}
                  <Badge type={up ? 'won' : 'lost'}>{up ? '+' : ''}£{pnl.toFixed(2)}</Badge>
                </div>
              </div>

              {/* ── Stats 2×3 ── */}
              <div style={{ opacity: decomm ? 0.45 : 1, pointerEvents: decomm ? 'none' : 'auto' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
                  {[
                    { label: 'Bankroll',    value: `£${(+(a.bankroll || 0)).toFixed(2)}`,    color: up ? tokens.colors.green : tokens.colors.red },
                    { label: 'Total Picks', value: a.total_picks || 0 },
                    { label: 'Win Rate',    value: `${a.win_rate || 0}%` },
                    { label: 'Threshold',   value: (+(a.confidence_threshold || 0)).toFixed(3) },
                    { label: 'CLV Avg',     value: `${(a.clv_avg || 0) >= 0 ? '+' : ''}${a.clv_avg || 0}%`, color: (a.clv_avg || 0) >= 0 ? tokens.colors.blue : tokens.colors.red },
                    { label: 'Updates',     value: a.update_count || 0 },
                  ].map(({ label, value, color }) => (
                    <div key={label} style={{
                      padding: '8px 10px',
                      border: `1px solid ${tokens.colors.border}`,
                      background: tokens.colors.surface2,
                    }}>
                      <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.1em', textTransform: 'uppercase', marginBottom: 4 }}>{label}</div>
                      <div style={{ fontSize: 14, fontWeight: 500, color: color || tokens.colors.text }}>{value}</div>
                    </div>
                  ))}
                </div>

                <WeightBar stat={a.statistical_weight || 0.5} mkt={a.market_weight || 0.5} />
              </div>

              {/* ── Action button (full-width, 44px tap target) ── */}
              <button
                onClick={() => handleToggle(a.agent_id, decomm)}
                disabled={busy === a.agent_id}
                style={{
                  marginTop: 12,
                  width: '100%',
                  minHeight: 44,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, letterSpacing: '.12em', textTransform: 'uppercase',
                  border: `1px solid ${decomm ? tokens.colors.green : tokens.colors.red}`,
                  background: decomm ? tokens.colors.greenDim : tokens.colors.redDim,
                  color: decomm ? tokens.colors.green : tokens.colors.red,
                  cursor: busy === a.agent_id ? 'not-allowed' : 'pointer',
                  opacity: busy === a.agent_id ? 0.5 : 1,
                  fontFamily: 'inherit',
                  WebkitTapHighlightColor: 'transparent',
                }}
              >
                {busy === a.agent_id ? 'Working…' : decomm ? 'Recommission' : 'Decommission'}
              </button>
            </Card>
          );
        })}
        {!agents.length && !loading && (
          <div style={{ color: tokens.colors.muted, fontSize: 12, padding: '8px 0' }}>No agents found.</div>
        )}
      </div>
    </div>
  );
}
