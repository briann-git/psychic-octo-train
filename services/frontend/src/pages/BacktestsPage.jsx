import { useState, useCallback } from 'react';
import tokens from '../tokens';
import Card from '../components/primitives/Card';
import CardTitle from '../components/primitives/CardTitle';
import SectionTitle from '../components/primitives/SectionTitle';
import Badge from '../components/primitives/Badge';
import useApi from '../hooks/useApi';
import { fetchBacktestReports, fetchBacktestReport, deleteBacktestReport } from '../api/endpoints';

const LEAGUE_LABELS = {
  EPL: 'Premier League', EFL_Championship: 'Championship',
  Bundesliga1: 'Bundesliga 1', Bundesliga2: 'Bundesliga 2',
  Ligue1: 'Ligue 1', Ligue2: 'Ligue 2',
  La_Liga: 'La Liga', La_Liga2: 'La Liga 2',
  Serie_A: 'Serie A', Serie_B: 'Serie B',
};

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

function fmtPct(v) {
  if (v == null) return '—';
  return `${v >= 0 ? '+' : ''}${(+v).toFixed(1)}%`;
}

function fmtPound(v) {
  if (v == null) return '—';
  return `${v >= 0 ? '+' : ''}£${(+v).toFixed(2)}`;
}

// ── Equity curve chart (pure SVG, no deps) ───────────────────────────────────

function EquityCurveChart({ equityCurve, startingBankroll = 1000 }) {
  if (!equityCurve || equityCurve.length === 0) {
    return <div style={{ color: tokens.colors.muted, fontSize: 12 }}>No equity data.</div>;
  }

  const bankrolls = equityCurve.map(p => p.bankroll);
  const minB = Math.min(...bankrolls, startingBankroll) * 0.98;
  const maxB = Math.max(...bankrolls, startingBankroll) * 1.02;
  const range = maxB - minB || 1;

  const W = 600, H = 180, PAD = { top: 12, right: 12, bottom: 24, left: 52 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;

  const xs = equityCurve.map((_, i) => PAD.left + (i / Math.max(equityCurve.length - 1, 1)) * chartW);
  const ys = bankrolls.map(b => PAD.top + chartH - ((b - minB) / range) * chartH);

  const polyline = xs.map((x, i) => `${x},${ys[i]}`).join(' ');
  const areaPoints = `${xs[0]},${PAD.top + chartH} ${polyline} ${xs[xs.length - 1]},${PAD.top + chartH}`;

  const yBaseline = PAD.top + chartH - ((startingBankroll - minB) / range) * chartH;

  // Y-axis labels (4 ticks)
  const yTicks = [0, 0.33, 0.66, 1].map(t => ({
    y: PAD.top + chartH - t * chartH,
    label: `£${Math.round(minB + t * range)}`,
  }));

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      style={{ width: '100%', height: 180, display: 'block', overflow: 'visible' }}
    >
      {/* Baseline (starting bankroll) */}
      <line
        x1={PAD.left} y1={yBaseline}
        x2={W - PAD.right} y2={yBaseline}
        stroke={tokens.colors.border2} strokeDasharray="3 3" strokeWidth="1"
      />

      {/* Area fill */}
      <polygon points={areaPoints} fill={tokens.colors.blueDim} />

      {/* Line */}
      <polyline
        points={polyline}
        fill="none"
        stroke={tokens.colors.blue}
        strokeWidth="1.5"
        strokeLinejoin="round"
      />

      {/* Y-axis ticks */}
      {yTicks.map(({ y, label }) => (
        <g key={label}>
          <line x1={PAD.left - 4} y1={y} x2={PAD.left} y2={y} stroke={tokens.colors.border} strokeWidth="1" />
          <text x={PAD.left - 7} y={y + 3.5} textAnchor="end" fontSize="9" fill={tokens.colors.dim}>{label}</text>
        </g>
      ))}

      {/* Axis lines */}
      <line x1={PAD.left} y1={PAD.top} x2={PAD.left} y2={PAD.top + chartH} stroke={tokens.colors.border} strokeWidth="1" />
      <line x1={PAD.left} y1={PAD.top + chartH} x2={W - PAD.right} y2={PAD.top + chartH} stroke={tokens.colors.border} strokeWidth="1" />
    </svg>
  );
}

// ── Outcome bar chart ─────────────────────────────────────────────────────────

function OutcomeChart({ equityCurve }) {
  const won  = equityCurve.filter(p => p.outcome === 'won').length;
  const lost = equityCurve.filter(p => p.outcome === 'lost').length;
  const void_ = equityCurve.filter(p => p.outcome === 'void').length;
  const skipped = equityCurve.filter(p => p.recommendation !== 'back').length;
  const total = won + lost + void_;
  if (total === 0) return null;

  const bars = [
    { label: 'Won',    count: won,   color: tokens.colors.green },
    { label: 'Lost',   count: lost,  color: tokens.colors.red   },
    { label: 'Void',   count: void_, color: tokens.colors.dim   },
    { label: 'Skipped', count: skipped, color: tokens.colors.border2 },
  ];
  const maxCount = Math.max(...bars.map(b => b.count), 1);

  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end', height: 80 }}>
      {bars.map(({ label, count, color }) => (
        <div key={label} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
          <div style={{ fontSize: 10, color: tokens.colors.muted }}>{count}</div>
          <div style={{
            width: '100%',
            height: Math.max((count / maxCount) * 54, 3),
            background: color,
            opacity: 0.8,
          }} />
          <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.06em' }}>{label}</div>
        </div>
      ))}
    </div>
  );
}

// ── Market breakdown ──────────────────────────────────────────────────────────

function MarketBreakdown({ byMarket }) {
  if (!byMarket || !byMarket.length) return <div style={{ fontSize: 11, color: tokens.colors.muted }}>No data.</div>;

  const COL = '1fr 56px 40px 40px 52px 80px';
  const headerCell = { textAlign: 'right' };
  const cell       = { textAlign: 'right' };

  return (
    <div>
      <div style={{
        display: 'grid', gridTemplateColumns: COL,
        gap: '4px 0', alignItems: 'center',
        fontSize: 9, color: tokens.colors.muted, letterSpacing: '.1em', textTransform: 'uppercase',
        borderBottom: `1px solid ${tokens.colors.border}`, paddingBottom: 6, marginBottom: 4,
      }}>
        <span>Market</span>
        <span style={headerCell}>Picks</span>
        <span style={headerCell}>W</span>
        <span style={headerCell}>L</span>
        <span style={headerCell}>WR</span>
        <span style={headerCell}>Net P&L</span>
      </div>
      {byMarket.map(m => (
        <div key={m.market} style={{
          display: 'grid', gridTemplateColumns: COL,
          gap: '4px 0', alignItems: 'center',
          padding: '6px 0', borderBottom: `1px solid ${tokens.colors.border}`, fontSize: 12,
        }}>
          <span style={{ color: tokens.colors.text, textTransform: 'capitalize' }}>
            {(m.market || '').replace(/_/g, ' ')}
          </span>
          <span style={{ ...cell, color: tokens.colors.muted }}>{m.picks}</span>
          <span style={{ ...cell, color: tokens.colors.green }}>{m.won}</span>
          <span style={{ ...cell, color: tokens.colors.red }}>{m.lost}</span>
          <span style={{ ...cell, color: m.win_rate >= 50 ? tokens.colors.green : tokens.colors.muted }}>
            {m.win_rate?.toFixed(0)}%
          </span>
          <span style={{ ...cell, color: (m.net_pnl ?? 0) >= 0 ? tokens.colors.green : tokens.colors.red }}>
            {fmtPound(m.net_pnl)}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Full report view ──────────────────────────────────────────────────────────

function ReportView({ reportId, onBack }) {
  const fetcher = useCallback(() => fetchBacktestReport(reportId), [reportId]);
  const { data: report, loading } = useApi(fetcher, { interval: 0 });

  if (loading) return <div style={{ color: tokens.colors.muted, fontSize: 12, padding: 24 }}>Loading report…</div>;
  if (!report) return <div style={{ color: tokens.colors.red, fontSize: 12, padding: 24 }}>Report not found.</div>;

  const pnl    = report.pnl_summary || {};
  const byAgent  = pnl.by_agent  || [];
  const byMarket = pnl.by_market || [];
  const ec     = report.equity_curve || [];

  const totalNet    = pnl.net_pnl ?? 0;
  const roi         = (pnl.roi ?? 0) * 100;
  const winRate     = ec.filter(p => p.outcome === 'won').length /
    Math.max(ec.filter(p => p.outcome != null).length, 1) * 100;

  const firstDate = ec[0]?.fixture_date;
  const lastDate  = ec[ec.length - 1]?.fixture_date;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <div
          onClick={onBack}
          style={{ fontSize: 11, cursor: 'pointer', color: tokens.colors.blue, letterSpacing: '.06em' }}
        >← All Reports</div>
        <div style={{ fontSize: 13, color: tokens.colors.text }}>
          {LEAGUE_LABELS[report.league] || report.league} — {report.season.slice(0,2)}/{report.season.slice(2)}
        </div>
        <div style={{ fontSize: 10, color: tokens.colors.muted }}>
          {fmtDate(report.created_at)}
        </div>
      </div>

      {/* Summary stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10, marginBottom: 16 }} className="fade-in s1">
        {[
          { label: 'Net P&L',    value: fmtPound(totalNet), color: totalNet >= 0 ? tokens.colors.green : tokens.colors.red },
          { label: 'ROI',        value: fmtPct(roi),         color: roi >= 0 ? tokens.colors.green : tokens.colors.red },
          { label: 'Win Rate',   value: `${winRate.toFixed(0)}%`, color: tokens.colors.text },
          { label: 'Picks Made', value: report.picks_made,   color: tokens.colors.blue },
          { label: 'Fixtures',   value: report.fixtures_processed, color: tokens.colors.muted },
        ].map(({ label, value, color }) => (
          <Card key={label} style={{ padding: '10px 14px' }}>
            <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.15em', textTransform: 'uppercase', marginBottom: 6 }}>{label}</div>
            <div style={{ fontSize: 20, fontWeight: 500, color }}>{value}</div>
          </Card>
        ))}
      </div>

      {/* Date range */}
      {(firstDate || lastDate) && (
        <div style={{ marginBottom: 16, fontSize: 11, color: tokens.colors.muted }}>
          {fmtDate(firstDate)} — {fmtDate(lastDate)}
        </div>
      )}

      {/* Equity curve */}
      <Card style={{ marginBottom: 16 }} className="fade-in s2">
        <CardTitle>Equity Curve</CardTitle>
        <EquityCurveChart equityCurve={ec} />
      </Card>

      {/* Outcome + Market side by side */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 12, marginBottom: 16 }} className="fade-in s3">
        <Card>
          <CardTitle>Outcomes</CardTitle>
          <OutcomeChart equityCurve={ec} />
        </Card>
        <Card>
          <CardTitle>By Market</CardTitle>
          <MarketBreakdown byMarket={byMarket} />
        </Card>
      </div>

      {/* Per-agent section */}
      {byAgent.length > 0 && (
        <>
          <SectionTitle>By Agent</SectionTitle>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }} className="fade-in s4">
            {byAgent.map(a => (
              <Card key={a.agent_id}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                  <span style={{ fontSize: 20, fontWeight: 600 }}>{a.agent_id}</span>
                  <Badge type={(a.net_pnl ?? 0) >= 0 ? 'won' : 'lost'}>{fmtPound(a.net_pnl)}</Badge>
                </div>
                {[
                  { label: 'ROI',      value: fmtPct((a.roi ?? 0) * 100), color: (a.roi ?? 0) >= 0 ? tokens.colors.green : tokens.colors.red },
                  { label: 'Win Rate', value: `${a.win_rate?.toFixed(0) ?? '—'}%`, color: tokens.colors.text },
                  { label: 'CLV Avg',  value: fmtPct(a.clv_avg),   color: (a.clv_avg ?? 0) >= 0 ? tokens.colors.blue : tokens.colors.red },
                  { label: 'Picks',    value: `${a.won ?? 0}W / ${a.lost ?? 0}L`, color: tokens.colors.muted },
                ].map(({ label, value, color }) => (
                  <div key={label} style={{ marginBottom: 7 }}>
                    <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.1em', textTransform: 'uppercase', marginBottom: 2 }}>{label}</div>
                    <div style={{ fontSize: 12, color }}>{value}</div>
                  </div>
                ))}
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ── Reports list ──────────────────────────────────────────────────────────────

function ReportsList({ profileId, onOpen, profiles }) {
  const fetcher = useCallback(() => fetchBacktestReports(profileId), [profileId]);
  const { data: reports, loading, reload } = useApi(fetcher, { interval: 0 });

  const profileName = (id) => (profiles || []).find(p => p.id === id)?.name || id?.slice(0, 8);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!confirm('Delete this backtest report?')) return;
    await deleteBacktestReport(id);
    reload();
  };

  if (loading) return <div style={{ color: tokens.colors.muted, fontSize: 12 }}>Loading…</div>;
  if (!reports?.length) {
    return (
      <div style={{ color: tokens.colors.muted, fontSize: 12, padding: '24px 0', lineHeight: 1.9 }}>
        No backtest reports yet.<br />
        Go to <strong style={{ color: tokens.colors.text }}>Profiles</strong> and click <strong style={{ color: tokens.colors.blue }}>Backtest</strong> on any profile.
      </div>
    );
  }

  return (
    <div>
      {(reports || []).map(r => {
        const pnl = r.pnl_summary || {};
        const net = pnl.net_pnl ?? 0;
        const roi = (pnl.roi ?? 0) * 100;

        return (
          <div
            key={r.id}
            onClick={() => onOpen(r.id)}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '11px 14px', marginBottom: 4, cursor: 'pointer',
              border: `1px solid ${tokens.colors.border}`,
              background: tokens.colors.surface,
              transition: 'border-color .15s',
            }}
            onMouseEnter={e => e.currentTarget.style.borderColor = tokens.colors.blue}
            onMouseLeave={e => e.currentTarget.style.borderColor = tokens.colors.border}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div>
                <div style={{ fontSize: 12, color: tokens.colors.text, marginBottom: 3 }}>
                  {LEAGUE_LABELS[r.league] || r.league}
                  <span style={{ color: tokens.colors.muted, marginLeft: 6 }}>
                    {r.season.slice(0,2)}/{r.season.slice(2)}
                  </span>
                </div>
                <div style={{ fontSize: 10, color: tokens.colors.muted }}>
                  {profileName(r.profile_id)} · {fmtDate(r.created_at)}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 11, color: tokens.colors.muted, marginBottom: 2, letterSpacing: '.06em' }}>Net P&L</div>
                <div style={{ fontSize: 13, color: net >= 0 ? tokens.colors.green : tokens.colors.red, fontWeight: 500 }}>
                  {fmtPound(net)}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 11, color: tokens.colors.muted, marginBottom: 2, letterSpacing: '.06em' }}>ROI</div>
                <div style={{ fontSize: 13, color: roi >= 0 ? tokens.colors.green : tokens.colors.red }}>
                  {fmtPct(roi)}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 11, color: tokens.colors.muted, marginBottom: 2, letterSpacing: '.06em' }}>Picks</div>
                <div style={{ fontSize: 13, color: tokens.colors.text }}>{r.picks_made}</div>
              </div>
              <div
                onClick={(e) => handleDelete(e, r.id)}
                style={{ fontSize: 11, color: tokens.colors.red, cursor: 'pointer', padding: '2px 4px' }}
              >✕</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function BacktestsPage({ profileId, profiles }) {
  const [openReportId, setOpenReportId] = useState(null);

  return (
    <div>
      {openReportId ? (
        <ReportView reportId={openReportId} onBack={() => setOpenReportId(null)} />
      ) : (
        <>
          <SectionTitle>Backtest Reports</SectionTitle>
          <ReportsList
            profileId={profileId}
            profiles={profiles}
            onOpen={setOpenReportId}
          />
        </>
      )}
    </div>
  );
}
