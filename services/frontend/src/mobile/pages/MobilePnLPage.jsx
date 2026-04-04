import { useCallback } from 'react';
import tokens from '../../tokens';
import Card from '../../components/primitives/Card';
import Badge from '../../components/primitives/Badge';
import useApi from '../../hooks/useApi';
import { fetchPnl } from '../../api/endpoints';

export default function MobilePnLPage({ profileId }) {
  const { data, loading } = useApi(
    useCallback(() => fetchPnl(profileId), [profileId]),
    { interval: 30000 }
  );

  const agents      = data?.agents      || [];
  const dailySeries = data?.daily_series || [];

  const totalNet    = agents.reduce((s, a) => s + (a.net_pnl || 0), 0);
  const totalStaked = agents.reduce((s, a) => s + (a.total_picks || 0) * 10, 0);
  const roi         = totalStaked ? ((totalNet / totalStaked) * 100).toFixed(2) : '0.00';
  const avgClv      = agents.length
    ? (agents.reduce((s, a) => s + (a.clv_avg || 0), 0) / agents.length).toFixed(2)
    : '0.00';

  const maxCumulative = dailySeries.length ? Math.max(...dailySeries.map(d => d.cumulative_pnl), 1) : 1;

  return (
    <div>
      {/* ── Summary metrics 2×2 ───────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }} className="fade-in s1">
        {[
          { label: 'Net P&L', value: `${totalNet >= 0 ? '+' : ''}£${totalNet.toFixed(2)}`, color: totalNet >= 0 ? tokens.colors.green : tokens.colors.red },
          { label: 'ROI',     value: `${roi >= 0 ? '+' : ''}${roi}%`,                       color: +roi >= 0 ? tokens.colors.green : tokens.colors.red },
          { label: 'Avg CLV', value: `${+avgClv >= 0 ? '+' : ''}${avgClv}%`,                color: tokens.colors.blue },
          { label: 'Days',    value: dailySeries.length || '—',                              color: tokens.colors.muted },
        ].map(({ label, value, color }) => (
          <Card key={label} style={{ padding: 12 }}>
            <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.12em', textTransform: 'uppercase', marginBottom: 6 }}>{label}</div>
            <div style={{ fontSize: 20, fontWeight: 500, color }}>{value}</div>
          </Card>
        ))}
      </div>

      {/* ── Cumulative P&L chart ─────────────────────────────────── */}
      <Card style={{ marginBottom: 12, padding: 12 }} className="fade-in s2">
        <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.15em', textTransform: 'uppercase', marginBottom: 8 }}>
          Cumulative P&L
        </div>
        {loading && <div style={{ color: tokens.colors.muted, fontSize: 12 }}>Loading…</div>}
        {!loading && !dailySeries.length && (
          <div style={{ color: tokens.colors.muted, fontSize: 12 }}>No settled picks yet.</div>
        )}
        {dailySeries.length > 0 && (
          <div style={{ height: 120, display: 'flex', alignItems: 'flex-end', gap: 2, padding: '4px 0' }}>
            {dailySeries.map((d, i) => {
              const h = maxCumulative > 0 ? Math.max((d.cumulative_pnl / maxCumulative) * 96, 3) : 3;
              return (
                <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                  <div style={{
                    width: '100%', height: h,
                    background: d.cumulative_pnl >= 0 ? tokens.colors.greenDim : tokens.colors.redDim,
                    borderTop: `2px solid ${d.cumulative_pnl >= 0 ? tokens.colors.green : tokens.colors.red}`,
                  }} />
                  {dailySeries.length <= 14 && (
                    <div style={{ fontSize: 8, color: tokens.colors.dim, writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>
                      {d.date?.slice(5)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>

      {/* ── Per-agent cards ──────────────────────────────────────── */}
      <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.2em', textTransform: 'uppercase', marginBottom: 6 }} className="fade-in s3">
        Per Agent
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 8 }} className="fade-in s3">
        {!agents.length && !loading && (
          <div style={{ color: tokens.colors.muted, fontSize: 12, padding: '8px 0' }}>No P&L data yet.</div>
        )}
        {agents.map(a => (
          <Card key={a.agent_id} style={{ padding: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <span style={{ fontSize: 20, fontWeight: 600 }}>{a.agent_id}</span>
              <Badge type={a.net_pnl >= 0 ? 'won' : 'lost'}>
                {a.net_pnl >= 0 ? '+' : ''}£{(+a.net_pnl).toFixed(2)}
              </Badge>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              {[
                { label: 'ROI',      value: `${a.roi >= 0 ? '+' : ''}${a.roi}%`,     color: a.roi >= 0 ? tokens.colors.green : tokens.colors.red },
                { label: 'Win Rate', value: `${a.win_rate}%`,                          color: tokens.colors.text },
                { label: 'CLV Avg',  value: `${a.clv_avg >= 0 ? '+' : ''}${a.clv_avg}%`, color: a.clv_avg >= 0 ? tokens.colors.blue : tokens.colors.red },
                { label: 'Picks',    value: `${a.won}W / ${a.lost}L / ${a.pending}P`, color: tokens.colors.muted },
              ].map(({ label, value, color }) => (
                <div key={label}>
                  <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.1em', textTransform: 'uppercase', marginBottom: 2 }}>{label}</div>
                  <div style={{ fontSize: 12, color }}>{value}</div>
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
