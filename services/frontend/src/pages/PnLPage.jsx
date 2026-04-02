import tokens from '../tokens';
import Card from '../components/primitives/Card';
import CardTitle from '../components/primitives/CardTitle';
import SectionTitle from '../components/primitives/SectionTitle';
import Badge from '../components/primitives/Badge';
import useApi from '../hooks/useApi';
import { fetchPnl } from '../api/endpoints';

import { useCallback } from 'react';

export default function PnLPage({ profileId }) {
  const { data, loading } = useApi(useCallback(() => fetchPnl(profileId), [profileId]), { interval: 30000 });
  const agents     = data?.agents     || [];
  const dailySeries = data?.daily_series || [];

  const totalNet  = agents.reduce((s, a) => s + (a.net_pnl || 0), 0);
  const totalStaked = agents.reduce((s, a) => s + (a.total_picks || 0) * 10, 0);
  const roi = totalStaked ? ((totalNet / totalStaked) * 100).toFixed(2) : '0.00';
  const avgClv = agents.length
    ? (agents.reduce((s, a) => s + (a.clv_avg || 0), 0) / agents.length).toFixed(2)
    : '0.00';

  const maxCumulative = dailySeries.length ? Math.max(...dailySeries.map(d => d.cumulative_pnl), 1) : 1;

  return (
    <div>
      <SectionTitle>P&L</SectionTitle>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 16 }} className="fade-in s1">
        {[
          { label: 'Net P&L',  value: `${totalNet >= 0 ? '+' : ''}£${totalNet.toFixed(2)}`, color: totalNet >= 0 ? tokens.colors.green : tokens.colors.red },
          { label: 'ROI',      value: `${roi >= 0 ? '+' : ''}${roi}%`,                       color: +roi >= 0 ? tokens.colors.green : tokens.colors.red },
          { label: 'Avg CLV',  value: `${+avgClv >= 0 ? '+' : ''}${avgClv}%`,                color: tokens.colors.blue },
          { label: 'Days',     value: dailySeries.length || '—',                              color: tokens.colors.muted },
        ].map(({ label, value, color }) => (
          <Card key={label}>
            <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.15em', textTransform: 'uppercase', marginBottom: 8 }}>{label}</div>
            <div style={{ fontSize: 26, fontWeight: 500, color }}>{value}</div>
          </Card>
        ))}
      </div>

      <Card style={{ marginBottom: 16 }} className="fade-in s2">
        <CardTitle>Cumulative P&L</CardTitle>
        {loading && <div style={{ color: tokens.colors.muted, fontSize: 12 }}>Loading…</div>}
        {!loading && !dailySeries.length && <div style={{ color: tokens.colors.muted, fontSize: 12 }}>No settled picks yet.</div>}
        {dailySeries.length > 0 && (
          <div style={{ height: 160, display: 'flex', alignItems: 'flex-end', gap: 3, padding: '8px 0' }}>
            {dailySeries.map((d, i) => {
              const h = maxCumulative > 0 ? Math.max((d.cumulative_pnl / maxCumulative) * 130, 3) : 3;
              return (
                <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                  <div style={{
                    width: '100%', height: h,
                    background: d.cumulative_pnl >= 0 ? tokens.colors.greenDim : tokens.colors.redDim,
                    borderTop: `2px solid ${d.cumulative_pnl >= 0 ? tokens.colors.green : tokens.colors.red}`,
                  }} />
                  <div style={{ fontSize: 9, color: tokens.colors.muted, writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>
                    {d.date?.slice(5)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <SectionTitle>Per Agent</SectionTitle>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12 }} className="fade-in s3">
        {agents.map(a => (
          <Card key={a.agent_id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
              <span style={{ fontSize: 20, fontWeight: 600 }}>{a.agent_id}</span>
              <Badge type={a.net_pnl >= 0 ? 'won' : 'lost'}>{a.net_pnl >= 0 ? '+' : ''}£{(+a.net_pnl).toFixed(2)}</Badge>
            </div>
            {[
              { label: 'ROI',       value: `${a.roi >= 0 ? '+' : ''}${a.roi}%`,     color: a.roi >= 0 ? tokens.colors.green : tokens.colors.red },
              { label: 'Win Rate',  value: `${a.win_rate}%`,                          color: tokens.colors.text },
              { label: 'CLV Avg',   value: `${a.clv_avg >= 0 ? '+' : ''}${a.clv_avg}%`, color: a.clv_avg >= 0 ? tokens.colors.blue : tokens.colors.red },
              { label: 'Picks',     value: `${a.won}W / ${a.lost}L / ${a.pending}P`, color: tokens.colors.muted },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.1em', textTransform: 'uppercase', marginBottom: 3 }}>{label}</div>
                <div style={{ fontSize: 13, color }}>{value}</div>
              </div>
            ))}
          </Card>
        ))}
        {!agents.length && !loading && <div style={{ color: tokens.colors.muted, fontSize: 12 }}>No P&L data yet.</div>}
      </div>
    </div>
  );
}
