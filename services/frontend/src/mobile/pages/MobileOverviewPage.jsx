import { useCallback } from 'react';
import tokens from '../../tokens';
import Card from '../../components/primitives/Card';
import Badge from '../../components/primitives/Badge';
import AgentTag from '../../components/primitives/AgentTag';
import WeightBar from '../../components/primitives/WeightBar';
import Sparkline from '../../components/primitives/Sparkline';
import useApi from '../../hooks/useApi';
import useTimezone from '../../hooks/useTimezone';
import { fetchStatus, fetchAgents, fetchPicks, fetchFixtures } from '../../api/endpoints';

export default function MobileOverviewPage({ profileId }) {
  const { fmt } = useTimezone();
  const today = fmt.isoDate();

  const { data: status }   = useApi(fetchStatus,   { interval: 15000 });
  const { data: agents }   = useApi(useCallback(() => fetchAgents(profileId),                       [profileId]), { interval: 30000 });
  const { data: picks }    = useApi(useCallback(() => fetchPicks({ limit: 6, profileId }),          [profileId]), { interval: 30000 });
  const { data: fixtures } = useApi(useCallback(() => fetchFixtures({ date: today }),               [today]),     { interval: 60000 });

  const allAgents = agents   || [];
  const allPicks  = picks    || [];
  const allFix    = fixtures || [];

  const settled      = allPicks.filter(p => p.outcome === 'won' || p.outcome === 'lost');
  const won          = allPicks.filter(p => p.outcome === 'won').length;
  const totalBankroll = allAgents.reduce((s, a) => s + (a.bankroll || 0), 0);
  const netPnl        = allAgents.reduce((s, a) => s + ((a.bankroll || 0) - (a.starting_bankroll || 1000)), 0);
  const winRate       = settled.length ? Math.round(won / settled.length * 100) : 0;

  const metrics = [
    { label: 'Bankroll', value: allAgents.length ? `£${totalBankroll.toFixed(2)}` : '—', color: tokens.colors.green,  spark: [50,65,45,80,60,90,55,85,70,100] },
    { label: 'Net P&L',  value: allAgents.length ? `${netPnl >= 0 ? '+' : ''}£${netPnl.toFixed(2)}` : '—', color: netPnl >= 0 ? tokens.colors.green : tokens.colors.red, spark: [30,45,35,70,40,85,55,90,60,75] },
    { label: 'Win Rate', value: settled.length ? `${winRate}%` : '—', color: tokens.colors.amber, spark: [60,60,40,80,60,60,40,60,100,60] },
    { label: 'Fixtures', value: allFix.length || '—', color: tokens.colors.text, spark: [20,40,30,80,60,40,70,50,90,60] },
  ];

  return (
    <div>
      {/* ── Scheduler status strip ─────────────────────────────────── */}
      {status && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '8px 10px', marginBottom: 12,
          border: `1px solid ${status.scheduler_running ? tokens.colors.border : tokens.colors.red}`,
          background: status.scheduler_running ? tokens.colors.surface : tokens.colors.redDim,
          fontSize: 11,
        }} className="fade-in s0">
          <div style={{
            width: 7, height: 7, borderRadius: '50%',
            background: status.scheduler_running ? tokens.colors.green : tokens.colors.red,
            animation: status.scheduler_running ? 'pulse 1s infinite' : 'none',
            flexShrink: 0,
          }} />
          <span style={{ color: status.scheduler_running ? tokens.colors.green : tokens.colors.red }}>
            {status.scheduler_running ? 'Scheduler running' : 'Scheduler stopped'}
          </span>
          {status.db_size && (
            <span style={{ marginLeft: 'auto', color: tokens.colors.dim, fontSize: 10 }}>{status.db_size}</span>
          )}
        </div>
      )}

      {/* ── Key metrics 2×2 ──────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }} className="fade-in s1">
        {metrics.map(({ label, value, color, spark }) => (
          <Card key={label} style={{ position: 'relative', overflow: 'hidden', padding: 12 }}>
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: color }} />
            <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.12em', textTransform: 'uppercase', marginBottom: 6 }}>{label}</div>
            <div style={{ fontSize: 20, fontWeight: 500, color, lineHeight: 1, marginBottom: 4 }}>{value}</div>
            <Sparkline data={spark} color={color} />
          </Card>
        ))}
      </div>

      {/* ── Agents ───────────────────────────────────────────────────── */}
      <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.2em', textTransform: 'uppercase', marginBottom: 6 }} className="fade-in s2">
        Agents
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 12 }} className="fade-in s2">
        {allAgents.length === 0 && (
          <div style={{ color: tokens.colors.muted, fontSize: 12, padding: '8px 0' }}>No agent data yet.</div>
        )}
        {allAgents.map(a => {
          const pnl = (a.bankroll || 0) - (a.starting_bankroll || 1000);
          const up  = pnl >= 0;
          return (
            <Card key={a.agent_id} style={{ padding: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 20, fontWeight: 600 }}>{a.agent_id}</span>
                  <span style={{ fontSize: 9, letterSpacing: '.12em', textTransform: 'uppercase', padding: '1px 5px', border: `1px solid ${tokens.colors.border2}`, color: tokens.colors.muted }}>
                    {a.staking_strategy || 'flat'}
                  </span>
                </div>
                <Badge type={up ? 'won' : 'lost'}>{up ? '+' : ''}£{pnl.toFixed(2)}</Badge>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
                {[
                  { label: 'Bankroll',  value: `£${(+(a.bankroll || 0)).toFixed(2)}`, color: up ? tokens.colors.green : tokens.colors.red },
                  { label: 'Win Rate',  value: `${a.win_rate || 0}%` },
                  { label: 'Picks',     value: a.total_picks || 0 },
                  { label: 'Threshold', value: (+(a.confidence_threshold || 0)).toFixed(3) },
                ].map(({ label, value, color }) => (
                  <div key={label}>
                    <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.1em', textTransform: 'uppercase', marginBottom: 2 }}>{label}</div>
                    <div style={{ fontSize: 13, color: color || tokens.colors.text }}>{value}</div>
                  </div>
                ))}
              </div>
              <WeightBar stat={a.statistical_weight || 0.5} mkt={a.market_weight || 0.5} />
            </Card>
          );
        })}
      </div>

      {/* ── Recent picks ─────────────────────────────────────────────── */}
      <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.2em', textTransform: 'uppercase', marginBottom: 6 }} className="fade-in s3">
        Recent Picks
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 8 }} className="fade-in s3">
        {allPicks.length === 0 && (
          <div style={{ color: tokens.colors.muted, fontSize: 12, padding: '8px 0' }}>No picks yet.</div>
        )}
        {allPicks.map((p, i) => (
          <Card key={i} style={{ padding: '10px 12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <AgentTag id={p.agent_id} />
                <span style={{ fontSize: 12 }}>{p.home_team} v {p.away_team}</span>
              </div>
              <Badge type={p.outcome || 'pending'}>{p.outcome || 'pending'}</Badge>
            </div>
            <div style={{ fontSize: 11, color: tokens.colors.muted }}>
              {p.league} · {p.selection} · {(+(p.odds || 0)).toFixed(2)}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
