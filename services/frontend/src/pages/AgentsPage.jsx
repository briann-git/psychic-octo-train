import tokens from '../tokens';
import Card from '../components/primitives/Card';
import SectionTitle from '../components/primitives/SectionTitle';
import Badge from '../components/primitives/Badge';
import WeightBar from '../components/primitives/WeightBar';
import useApi from '../hooks/useApi';
import { fetchAgents } from '../api/endpoints';

export default function AgentsPage() {
  const { data, loading } = useApi(fetchAgents, { interval: 30000 });
  const agents = data || [];

  return (
    <div>
      <SectionTitle>Agents</SectionTitle>
      {loading && <div style={{ color: tokens.colors.muted, fontSize: 12 }}>Loading…</div>}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 12 }} className="fade-in s1">
        {agents.map(a => {
          const pnl = (a.bankroll || 0) - (a.starting_bankroll || 1000);
          const pct = ((a.bankroll || 0) / (a.starting_bankroll || 1000)) * 100;
          const up  = pnl >= 0;
          return (
            <Card key={a.agent_id}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
                <div>
                  <div style={{ fontSize: 28, fontWeight: 600, marginBottom: 4 }}>Agent {a.agent_id}</div>
                  <div style={{ fontSize: 10, letterSpacing: '.15em', textTransform: 'uppercase', color: tokens.colors.muted }}>
                    {a.staking_strategy || 'flat'} staking
                    {a.staking_strategy === 'kelly' ? ` · kelly ${a.kelly_fraction}` : ''}
                  </div>
                </div>
                <Badge type={up ? 'won' : 'lost'}>{up ? '+' : ''}£{pnl.toFixed(2)}</Badge>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12, marginBottom: 16 }}>
                {[
                  { label: 'Bankroll',   value: `£${(+(a.bankroll || 0)).toFixed(2)}`,    color: up ? tokens.colors.green : tokens.colors.red },
                  { label: 'Total Picks', value: a.total_picks || 0 },
                  { label: 'Win Rate',   value: `${a.win_rate || 0}%` },
                  { label: 'Threshold',  value: (+(a.confidence_threshold || 0)).toFixed(3) },
                  { label: 'CLV Avg',    value: `${(a.clv_avg || 0) >= 0 ? '+' : ''}${a.clv_avg || 0}%`, color: (a.clv_avg || 0) >= 0 ? tokens.colors.blue : tokens.colors.red },
                  { label: 'Updates',    value: a.update_count || 0 },
                ].map(({ label, value, color }) => (
                  <div key={label} style={{ padding: '10px 12px', border: `1px solid ${tokens.colors.border}`, background: tokens.colors.surface2 }}>
                    <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.1em', textTransform: 'uppercase', marginBottom: 6 }}>{label}</div>
                    <div style={{ fontSize: 15, fontWeight: 500, color: color || tokens.colors.text }}>{value}</div>
                  </div>
                ))}
              </div>

              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 10, color: tokens.colors.muted, letterSpacing: '.12em', textTransform: 'uppercase', marginBottom: 8 }}>Signal Weights</div>
                <div style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
                  <div style={{ flex: a.statistical_weight || 0.5, height: 24, background: tokens.colors.greenDim, border: `1px solid ${tokens.colors.green}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: tokens.colors.green }}>
                    STAT {((a.statistical_weight || 0.5) * 100).toFixed(0)}%
                  </div>
                  <div style={{ flex: a.market_weight || 0.5, height: 24, background: tokens.colors.blueDim, border: `1px solid ${tokens.colors.blue}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: tokens.colors.blue }}>
                    MKT {((a.market_weight || 0.5) * 100).toFixed(0)}%
                  </div>
                </div>
              </div>

              <WeightBar stat={a.statistical_weight || 0.5} mkt={a.market_weight || 0.5} />

              <div style={{ fontSize: 10, color: tokens.colors.muted, letterSpacing: '.1em', textTransform: 'uppercase', marginBottom: 6, marginTop: 12 }}>Bankroll vs Starting</div>
              <div style={{ height: 5, background: tokens.colors.border, marginBottom: 4 }}>
                <div style={{ height: '100%', width: `${Math.min(pct, 100)}%`, background: up ? tokens.colors.green : tokens.colors.red, transition: 'width .5s' }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, color: tokens.colors.muted }}>
                <span>Start £{(+(a.starting_bankroll || 1000)).toFixed(2)}</span>
                <span style={{ color: up ? tokens.colors.green : tokens.colors.red }}>Now £{(+(a.bankroll || 0)).toFixed(2)}</span>
              </div>
            </Card>
          );
        })}
        {!agents.length && !loading && <div style={{ color: tokens.colors.muted, fontSize: 12 }}>No agent data yet.</div>}
      </div>
    </div>
  );
}
