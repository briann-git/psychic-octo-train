import { useCallback } from 'react';
import tokens from '../tokens';
import Card from '../components/primitives/Card';
import CardTitle from '../components/primitives/CardTitle';
import SectionTitle from '../components/primitives/SectionTitle';
import Badge from '../components/primitives/Badge';
import AgentTag from '../components/primitives/AgentTag';
import Sparkline from '../components/primitives/Sparkline';
import WeightBar from '../components/primitives/WeightBar';
import useApi from '../hooks/useApi';
import { fetchStatus, fetchAgents, fetchPicks, fetchFixtures, fetchJobs } from '../api/endpoints';
import useTimezone from '../hooks/useTimezone';

export default function OverviewPage({ profileId }) {
  const { fmt } = useTimezone();
  const today = fmt.isoDate();
  const { data: status }   = useApi(fetchStatus,   { interval: 15000 });
  const { data: agents }   = useApi(useCallback(() => fetchAgents(profileId), [profileId]),   { interval: 30000 });
  const { data: picks }    = useApi(useCallback(() => fetchPicks({ limit: 6, profileId }), [profileId]), { interval: 30000 });
  const { data: fixtures } = useApi(useCallback(() => fetchFixtures({ date: today }), [today]), { interval: 60000 });
  const { data: jobs }     = useApi(fetchJobs, { interval: 60000 });

  const allAgents = agents || [];
  const allPicks  = picks  || [];
  const allFix    = fixtures || [];

  const settled   = allPicks.filter(p => p.outcome === 'won' || p.outcome === 'lost');
  const won       = allPicks.filter(p => p.outcome === 'won').length;
  const totalBankroll = allAgents.reduce((s, a) => s + (a.bankroll || 0), 0);
  const netPnl = allAgents.reduce((s, a) => s + ((a.bankroll || 0) - (a.starting_bankroll || 1000)), 0);
  const winRate = settled.length ? Math.round(won / settled.length * 100) : 0;

  const metrics = [
    { label: 'Total Bankroll', value: allAgents.length ? `£${totalBankroll.toFixed(2)}` : '—', color: tokens.colors.green, spark: [50,65,45,80,60,90,55,85,70,100] },
    { label: 'Net P&L',        value: allAgents.length ? `${netPnl >= 0 ? '+' : ''}£${netPnl.toFixed(2)}` : '—', color: netPnl >= 0 ? tokens.colors.green : tokens.colors.red, spark: [30,45,35,70,40,85,55,90,60,75] },
    { label: 'Win Rate',       value: settled.length ? `${winRate}%` : '—', color: tokens.colors.amber, spark: [60,60,40,80,60,60,40,60,100,60] },
    { label: "Today's Fixtures", value: allFix.length ? allFix.length : '—', color: tokens.colors.text, spark: [20,40,30,80,60,40,70,50,90,60] },
  ];

  return (
    <div>
      <SectionTitle>Overview</SectionTitle>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 16 }} className="fade-in s1">
        {metrics.map(({ label, value, color, spark }) => (
          <Card key={label} style={{ position: 'relative', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: color }} />
            <div style={{ fontSize: 10, color: tokens.colors.muted, letterSpacing: '.15em', textTransform: 'uppercase', marginBottom: 8 }}>{label}</div>
            <div style={{ fontSize: 26, fontWeight: 500, color, lineHeight: 1, marginBottom: 6 }}>{value}</div>
            <Sparkline data={spark} color={color} />
          </Card>
        ))}
      </div>

      <SectionTitle>Agents</SectionTitle>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 16 }} className="fade-in s2">
        {allAgents.map(a => {
          const pnl = (a.bankroll || 0) - (a.starting_bankroll || 1000);
          const up  = pnl >= 0;
          return (
            <Card key={a.agent_id}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <span style={{ fontSize: 22, fontWeight: 600 }}>{a.agent_id}</span>
                <span style={{ fontSize: 9, letterSpacing: '.15em', textTransform: 'uppercase', padding: '2px 6px', border: `1px solid ${tokens.colors.border2}`, color: tokens.colors.muted }}>{a.staking_strategy || 'flat'}</span>
              </div>
              {[
                { label: 'Bankroll',      value: <span style={{ color: up ? tokens.colors.green : tokens.colors.red }}>£{(+(a.bankroll || 0)).toFixed(2)}</span> },
                { label: 'Picks / Win%',  value: `${a.total_picks || 0} / ${a.win_rate || 0}%` },
                { label: 'Threshold',     value: (+(a.confidence_threshold || 0)).toFixed(3) },
              ].map(({ label, value }) => (
                <div key={label} style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.1em', textTransform: 'uppercase', marginBottom: 3 }}>{label}</div>
                  <div style={{ fontSize: 13 }}>{value}</div>
                </div>
              ))}
              <WeightBar stat={a.statistical_weight || 0.5} mkt={a.market_weight || 0.5} />
            </Card>
          );
        })}
        {!allAgents.length && (
          <div style={{ gridColumn: '1/-1', color: tokens.colors.muted, fontSize: 12, padding: 16 }}>No agent data yet.</div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }} className="fade-in s3">
        <Card>
          <CardTitle>Recent Picks</CardTitle>
          {allPicks.length ? (
            <table>
              <thead><tr><th>Ag</th><th>Match</th><th>Sel</th><th>Odds</th><th>Status</th></tr></thead>
              <tbody>
                {allPicks.map((p, i) => (
                  <tr key={i}>
                    <td><AgentTag id={p.agent_id} /></td>
                    <td><span style={{ color: tokens.colors.muted, fontSize: 10 }}>{p.league} </span>{p.home} v {p.away}</td>
                    <td>{p.selection_id}</td>
                    <td>{(+(p.selection_odds || 0)).toFixed(2)}</td>
                    <td><Badge type={p.outcome || 'pending'}>{p.outcome || 'pending'}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <div style={{ color: tokens.colors.muted, fontSize: 12 }}>No picks yet.</div>}
        </Card>

        <Card>
          <CardTitle>Scheduler Status</CardTitle>
          {status ? (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 0', borderBottom: `1px solid ${tokens.colors.border}` }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: status.scheduler_running ? tokens.colors.green : tokens.colors.red,
                  animation: status.scheduler_running ? 'pulse 1s infinite' : 'none',
                }} />
                <span style={{ flex: 1, fontSize: 12 }}>Scheduler</span>
                <span style={{ fontSize: 10, color: status.scheduler_running ? tokens.colors.green : tokens.colors.red }}>
                  {status.scheduler_running ? 'Running' : 'Stopped'}
                </span>
              </div>
              {status.last_run && (
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '9px 0', borderBottom: `1px solid ${tokens.colors.border}`, fontSize: 12 }}>
                  <span style={{ color: tokens.colors.muted }}>Last pick</span>
                  <span>{fmt.date(status.last_run)}</span>
                </div>
              )}
              {status.db_size && (
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '9px 0', fontSize: 12 }}>
                  <span style={{ color: tokens.colors.muted }}>DB size</span>
                  <span>{status.db_size}</span>
                </div>
              )}
            </div>
          ) : <div style={{ color: tokens.colors.muted, fontSize: 12 }}>Loading…</div>}
        </Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }} className="fade-in s4">
        <Card>
          <CardTitle>Today's Fixtures</CardTitle>
          {allFix.slice(0, 6).map((f, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 0', borderBottom: `1px solid ${tokens.colors.border}`, fontSize: 12 }}>
              <span style={{ fontSize: 9, letterSpacing: '.1em', textTransform: 'uppercase', color: tokens.colors.muted, width: 60, flexShrink: 0 }}>{f.league}</span>
              <span style={{ flex: 1 }}>{f.home} v {f.away}</span>
              <span style={{ fontSize: 11, color: tokens.colors.muted, flexShrink: 0 }}>{f.kickoff ? fmt.time(f.kickoff) : ''}</span>
            </div>
          ))}
          {!allFix.length && <div style={{ color: tokens.colors.muted, fontSize: 12 }}>No fixtures today.</div>}
        </Card>

        <Card>
          <CardTitle>Scheduled Jobs</CardTitle>
          {(jobs || []).length ? (jobs || []).map(j => {
            const next = j.next_run ? new Date(j.next_run) : null;
            const now = Date.now();
            const diffMs = next ? next.getTime() - now : 0;
            const diffH = Math.floor(diffMs / 3_600_000);
            const diffM = Math.floor((diffMs % 3_600_000) / 60_000);
            const eta = diffMs > 0 ? (diffH > 0 ? `${diffH}h ${diffM}m` : `${diffM}m`) : 'due';
            return (
              <div key={j.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: `1px solid ${tokens.colors.border}`, fontSize: 12 }}>
                <span style={{ flex: 1 }}>{j.label}</span>
                <span style={{ fontSize: 10, color: tokens.colors.muted, flexShrink: 0 }}>{j.schedule}</span>
                <span style={{ fontSize: 10, color: tokens.colors.muted, flexShrink: 0 }}>{fmt.time(j.next_run)}</span>
                <span style={{ fontSize: 10, color: tokens.colors.amber, flexShrink: 0, minWidth: 50, textAlign: 'right' }}>{eta}</span>
              </div>
            );
          }) : <div style={{ color: tokens.colors.muted, fontSize: 12 }}>Loading…</div>}
        </Card>
      </div>
    </div>
  );
}
