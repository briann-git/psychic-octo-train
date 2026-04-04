import { useState, useCallback } from 'react';
import tokens from '../../tokens';
import Card from '../../components/primitives/Card';
import Badge from '../../components/primitives/Badge';
import AgentTag from '../../components/primitives/AgentTag';
import useApi from '../../hooks/useApi';
import { fetchPicks } from '../../api/endpoints';

const STATUSES = ['all', 'won', 'lost', 'pending'];

export default function MobilePicksFeedPage({ profileId }) {
  const [filter, setFilter] = useState('all');
  const { data, loading } = useApi(
    useCallback(() => fetchPicks({ limit: 200, profileId }), [profileId]),
    { interval: 30000 }
  );

  const picks   = data || [];
  const filtered = filter === 'all' ? picks
    : filter === 'pending' ? picks.filter(p => !p.outcome)
    : picks.filter(p => p.outcome === filter);

  const won     = picks.filter(p => p.outcome === 'won').length;
  const lost    = picks.filter(p => p.outcome === 'lost').length;
  const pending = picks.filter(p => !p.outcome).length;
  const netPnl  = picks.reduce((s, p) => s + (p.pnl || 0), 0);

  return (
    <div>
      {/* ── Summary strip ─────────────────────────────────────────── */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)',
        borderBottom: `1px solid ${tokens.colors.border}`,
        marginBottom: 12, marginLeft: -12, marginRight: -12,
      }} className="fade-in s1">
        {[
          { label: 'Total', value: picks.length,  color: tokens.colors.text },
          { label: 'Won',   value: won,            color: tokens.colors.green },
          { label: 'Lost',  value: lost,           color: tokens.colors.red },
          { label: 'Pend',  value: pending,        color: tokens.colors.amber },
          { label: 'P&L',   value: `${netPnl >= 0 ? '+' : ''}£${netPnl.toFixed(2)}`, color: netPnl >= 0 ? tokens.colors.green : tokens.colors.red },
        ].map(({ label, value, color }, idx, arr) => (
          <div key={label} style={{
            padding: '10px 0',
            borderRight: idx < arr.length - 1 ? `1px solid ${tokens.colors.border}` : 'none',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.12em', textTransform: 'uppercase', marginBottom: 4 }}>{label}</div>
            <div style={{ fontSize: 16, fontWeight: 500, color }}>{value}</div>
          </div>
        ))}
      </div>

      {/* ── Filter chips ──────────────────────────────────────────── */}
      <div style={{
        display: 'flex', gap: 6,
        overflowX: 'auto', WebkitOverflowScrolling: 'touch',
        marginBottom: 12, paddingBottom: 2,
      }} className="fade-in s2">
        {STATUSES.map(s => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            style={{
              flexShrink: 0,
              padding: '5px 12px', fontSize: 10,
              letterSpacing: '.1em', textTransform: 'uppercase',
              border: `1px solid ${filter === s ? tokens.colors.green : tokens.colors.border2}`,
              background: filter === s ? tokens.colors.greenDim : 'transparent',
              color: filter === s ? tokens.colors.green : tokens.colors.muted,
              cursor: 'pointer',
              WebkitTapHighlightColor: 'transparent',
            }}
          >{s}</button>
        ))}
      </div>

      {/* ── Pick cards ────────────────────────────────────────────── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }} className="fade-in s3">
        {loading && <div style={{ color: tokens.colors.muted, fontSize: 12, padding: '8px 0' }}>Loading…</div>}
        {!loading && filtered.length === 0 && (
          <div style={{ color: tokens.colors.muted, fontSize: 12, padding: '8px 0' }}>No picks found.</div>
        )}
        {filtered.map((p, i) => {
          const pnl = p.pnl;
          const clv = p.clv;
          return (
            <Card key={i} style={{ padding: '10px 12px' }}>
              {/* Row 1: agent + match + outcome */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 5 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, minWidth: 0 }}>
                  <AgentTag id={p.agent_id} />
                  <span style={{ fontSize: 12, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {p.home_team} v {p.away_team}
                  </span>
                </div>
                <Badge type={p.outcome || 'pending'}>{p.outcome || 'pending'}</Badge>
              </div>
              {/* Row 2: league · selection · odds · stake */}
              <div style={{ fontSize: 11, color: tokens.colors.muted, marginBottom: 5 }}>
                {p.league} · <span style={{ color: tokens.colors.text }}>{p.selection}</span> · {(+(p.odds || 0)).toFixed(2)} · £{(+(p.stake || 0)).toFixed(2)}
              </div>
              {/* Row 3: conf · P&L · CLV */}
              <div style={{ display: 'flex', gap: 14, fontSize: 11 }}>
                <span style={{ color: tokens.colors.blue }}>
                  Conf {p.stat_confidence != null ? `${(p.stat_confidence * 100).toFixed(1)}%` : '—'}
                </span>
                <span style={{ color: pnl == null ? tokens.colors.muted : pnl >= 0 ? tokens.colors.green : tokens.colors.red }}>
                  P&L {pnl == null ? '—' : `${pnl >= 0 ? '+' : ''}£${(+pnl).toFixed(2)}`}
                </span>
                <span style={{ color: clv == null ? tokens.colors.muted : clv >= 0 ? tokens.colors.green : tokens.colors.red }}>
                  CLV {clv == null ? '—' : `${clv >= 0 ? '+' : ''}${(+clv * 100).toFixed(1)}%`}
                </span>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
