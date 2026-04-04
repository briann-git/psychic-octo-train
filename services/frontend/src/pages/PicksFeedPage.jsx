import { useState, useCallback, useMemo } from 'react';
import tokens from '../tokens';
import Card from '../components/primitives/Card';
import SectionTitle from '../components/primitives/SectionTitle';
import Badge from '../components/primitives/Badge';
import AgentTag from '../components/primitives/AgentTag';
import useApi from '../hooks/useApi';
import useTimezone from '../hooks/useTimezone';
import { fetchPicks } from '../api/endpoints';

const STATUSES = ['all', 'won', 'lost', 'pending'];

const pill = (active) => ({
  padding: '4px 12px', fontSize: 11, borderRadius: 2, cursor: 'pointer',
  transition: 'all .15s', letterSpacing: '.05em', userSelect: 'none',
  border: `1px solid ${active ? tokens.colors.green : tokens.colors.border2}`,
  background: active ? tokens.colors.greenDim : 'transparent',
  color: active ? tokens.colors.green : tokens.colors.muted,
});

const navBtn = {
  padding: '4px 10px', fontSize: 11, cursor: 'pointer',
  border: `1px solid ${tokens.colors.border2}`, color: tokens.colors.muted,
  userSelect: 'none',
};

export default function PicksFeedPage({ profileId }) {
  const { fmt } = useTimezone();
  const [statusFilter, setStatusFilter] = useState('all');
  const [agentFilter,  setAgentFilter]  = useState('all');
  const [date,         setDate]         = useState(null); // null = all time

  const moveDate = (delta) => {
    const base = date ? date : fmt.isoDate();
    const d = new Date(base + 'T12:00:00');
    d.setDate(d.getDate() + delta);
    setDate(fmt.isoDate(d));
  };

  const fetchArgs = useMemo(
    () => ({ limit: 500, profileId, date: date || undefined }),
    [profileId, date],
  );

  const { data, loading } = useApi(
    useCallback(() => fetchPicks(fetchArgs), [fetchArgs]),
    { interval: 30000 },
  );

  const picks = data || [];
  const agents = useMemo(
    () => [...new Set(picks.map(p => p.agent_id).filter(Boolean))].sort(),
    [picks],
  );

  const filtered = useMemo(() => picks.filter(p => {
    const statusOk = statusFilter === 'all'     ? true
                   : statusFilter === 'pending' ? !p.outcome
                   : p.outcome === statusFilter;
    const agentOk = agentFilter === 'all' || p.agent_id === agentFilter;
    return statusOk && agentOk;
  }), [picks, statusFilter, agentFilter]);

  const won     = picks.filter(p => p.outcome === 'won').length;
  const lost    = picks.filter(p => p.outcome === 'lost').length;
  const pending = picks.filter(p => !p.outcome).length;
  const netPnl  = picks.reduce((s, p) => s + (p.pnl || 0), 0);

  return (
    <div>
      <SectionTitle>Picks Feed</SectionTitle>

      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 12, marginBottom: 16 }} className="fade-in s1">
        {[
          { label: 'Total',    value: picks.length,  color: tokens.colors.text },
          { label: 'Won',      value: won,           color: tokens.colors.green },
          { label: 'Lost',     value: lost,          color: tokens.colors.red },
          { label: 'Pending',  value: pending,       color: tokens.colors.amber },
          { label: 'Net P&L',  value: `${netPnl >= 0 ? '+' : ''}£${netPnl.toFixed(2)}`, color: netPnl >= 0 ? tokens.colors.green : tokens.colors.red },
        ].map(({ label, value, color }) => (
          <Card key={label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.15em', textTransform: 'uppercase', marginBottom: 8 }}>{label}</div>
            <div style={{ fontSize: 22, fontWeight: 500, color }}>{value}</div>
          </Card>
        ))}
      </div>

      {/* Filter bar */}
      <div style={{ background: tokens.colors.surface, border: `1px solid ${tokens.colors.border}`, padding: '10px 14px', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }} className="fade-in s2">

        {/* Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 10, color: tokens.colors.dim, textTransform: 'uppercase', letterSpacing: '.1em', marginRight: 2 }}>Status</span>
          {STATUSES.map(s => (
            <div key={s} onClick={() => setStatusFilter(s)} style={pill(statusFilter === s)}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </div>
          ))}
        </div>

        <div style={{ width: 1, height: 22, background: tokens.colors.border }} />

        {/* Agents */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 10, color: tokens.colors.dim, textTransform: 'uppercase', letterSpacing: '.1em', marginRight: 2 }}>Agent</span>
          {['all', ...agents].map(a => (
            <div key={a} onClick={() => setAgentFilter(a)} style={pill(agentFilter === a)}>
              {a === 'all' ? 'All' : `Agent ${a}`}
            </div>
          ))}
        </div>

        {/* Date nav — pushed right */}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
          <div onClick={() => moveDate(-1)} style={navBtn}>←</div>
          <input
            type="date"
            value={date || ''}
            onChange={e => setDate(e.target.value || null)}
            style={{ background: tokens.colors.surface2, border: `1px solid ${tokens.colors.border2}`, color: tokens.colors.text, padding: '4px 10px', fontSize: 11, fontFamily: tokens.fonts.mono }}
          />
          <div onClick={() => moveDate(1)} style={navBtn}>→</div>
          <div
            onClick={() => setDate(fmt.isoDate())}
            style={{ ...navBtn, color: tokens.colors.green, borderColor: tokens.colors.green }}
          >Today</div>
          {date && (
            <div onClick={() => setDate(null)} style={{ ...navBtn, color: tokens.colors.amber, borderColor: tokens.colors.amber }}>All time</div>
          )}
        </div>
      </div>

      {/* Scrollable table */}
      <Card className="fade-in s3" style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column', padding: 0 }}>
        {loading && <div style={{ padding: 16, color: tokens.colors.muted, fontSize: 12 }}>Loading…</div>}
        {!loading && !filtered.length && <div style={{ padding: 16, color: tokens.colors.muted, fontSize: 12 }}>No picks found.</div>}
        {filtered.length > 0 && (
          <div style={{ overflowY: 'auto', maxHeight: 'calc(100vh - 340px)' }}>
            <table style={{ minWidth: 900 }}>
              <thead style={{ position: 'sticky', top: 0, background: tokens.colors.surface, zIndex: 1 }}>
                <tr>
                  <th>Agent</th><th>League</th><th>Match</th><th>Market</th><th>Selection</th>
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
                      <td style={{ color: tokens.colors.muted, fontSize: 11 }}>{p.market}</td>
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
          </div>
        )}
      </Card>
    </div>
  );
}
