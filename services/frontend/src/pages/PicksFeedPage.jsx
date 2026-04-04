import { useState, useCallback } from 'react';
import tokens from '../tokens';
import Card from '../components/primitives/Card';
import SectionTitle from '../components/primitives/SectionTitle';
import Badge from '../components/primitives/Badge';
import AgentTag from '../components/primitives/AgentTag';
import useApi from '../hooks/useApi';
import { fetchPicks } from '../api/endpoints';

const STATUSES = ['all', 'won', 'lost', 'pending'];

export default function PicksFeedPage({ profileId }) {
  const [filter, setFilter] = useState('all');
  const { data, loading } = useApi(useCallback(() => fetchPicks({ limit: 200, profileId }), [profileId]), { interval: 30000 });

  const picks = data || [];
  const filtered = filter === 'all' ? picks : filter === 'pending'
    ? picks.filter(p => !p.outcome)
    : picks.filter(p => p.outcome === filter);

  const won     = picks.filter(p => p.outcome === 'won').length;
  const lost    = picks.filter(p => p.outcome === 'lost').length;
  const pending = picks.filter(p => !p.outcome).length;
  const netPnl  = picks.reduce((s, p) => s + (p.pnl || 0), 0);

  return (
    <div>
      <SectionTitle>Picks Feed</SectionTitle>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 12, marginBottom: 16 }} className="fade-in s1">
        {[
          { label: 'Total Picks', value: picks.length, color: tokens.colors.text },
          { label: 'Won',         value: won,           color: tokens.colors.green },
          { label: 'Lost',        value: lost,          color: tokens.colors.red },
          { label: 'Pending',     value: pending,       color: tokens.colors.amber },
          { label: 'Net P&L',     value: `${netPnl >= 0 ? '+' : ''}£${netPnl.toFixed(2)}`, color: netPnl >= 0 ? tokens.colors.green : tokens.colors.red },
        ].map(({ label, value, color }) => (
          <Card key={label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.15em', textTransform: 'uppercase', marginBottom: 8 }}>{label}</div>
            <div style={{ fontSize: 22, fontWeight: 500, color }}>{value}</div>
          </Card>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 0, borderBottom: `1px solid ${tokens.colors.border}`, marginBottom: 16 }} className="fade-in s2">
        {STATUSES.map(s => (
          <div key={s} onClick={() => setFilter(s)} style={{
            padding: '8px 16px', fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase',
            cursor: 'pointer',
            borderBottom: `2px solid ${filter === s ? tokens.colors.green : 'transparent'}`,
            color: filter === s ? tokens.colors.green : tokens.colors.muted,
            marginBottom: -1, transition: 'all .15s',
          }}>{s}</div>
        ))}
      </div>

      <Card className="fade-in s3">
        {loading && <div style={{ color: tokens.colors.muted, fontSize: 12 }}>Loading…</div>}
        {!loading && !filtered.length && <div style={{ color: tokens.colors.muted, fontSize: 12 }}>No picks found.</div>}
        {filtered.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Agent</th><th>League</th><th>Match</th><th>Selection</th>
                <th>Odds</th><th>Stake</th><th>Conf</th><th>Status</th><th>P&L</th><th>CLV</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p, i) => {
                const pnl = p.pnl;
                const clv = p.clv;
                return (
                  <tr key={i}>
                    <td><AgentTag id={p.agent_id} /></td>
                    <td style={{ color: tokens.colors.muted, fontSize: 11 }}>{p.league}</td>
                    <td>{p.home_team} v {p.away_team}</td>
                    <td style={{ fontWeight: 500 }}>{p.selection}</td>
                    <td>{(+(p.odds || 0)).toFixed(2)}</td>
                    <td>£{(+(p.stake || 0)).toFixed(2)}</td>
                    <td style={{ color: tokens.colors.blue }}>
                      {p.stat_confidence != null ? `${(p.stat_confidence * 100).toFixed(1)}%` : '—'}
                    </td>
                    <td><Badge type={p.outcome || 'pending'}>{p.outcome || 'pending'}</Badge></td>
                    <td style={{ color: pnl == null ? tokens.colors.muted : pnl >= 0 ? tokens.colors.green : tokens.colors.red }}>
                      {pnl == null ? '—' : `${pnl >= 0 ? '+' : ''}£${(+pnl).toFixed(2)}`}
                    </td>
                    <td style={{ color: clv == null ? tokens.colors.muted : clv >= 0 ? tokens.colors.green : tokens.colors.red }}>
                      {clv == null ? '—' : `${clv >= 0 ? '+' : ''}${(+clv * 100).toFixed(1)}%`}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
