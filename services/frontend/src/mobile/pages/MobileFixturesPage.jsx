import { useState, useCallback } from 'react';
import tokens from '../../tokens';
import Card from '../../components/primitives/Card';
import useApi from '../../hooks/useApi';
import useTimezone from '../../hooks/useTimezone';
import { fetchFixtures } from '../../api/endpoints';

// Cycling palette for per-league accent colours
const LEAGUE_PALETTE = [
  tokens.colors.green,
  tokens.colors.blue,
  tokens.colors.amber,
  '#a78bfa',
  '#f472b6',
  '#34d399',
  '#60a5fa',
];

export default function MobileFixturesPage() {
  const { fmt } = useTimezone();
  const [league, setLeague] = useState('all');
  const [date, setDate]     = useState(() => fmt.isoDate());

  const { data, loading } = useApi(
    useCallback(() => fetchFixtures({ date }), [date]),
    { interval: 60000 }
  );

  const fixtures = data || [];
  const leagues  = ['all', ...Array.from(new Set(fixtures.map(f => f.league))).sort()];
  const filtered = league === 'all' ? fixtures : fixtures.filter(f => f.league === league);

  // Map league name → accent colour
  const leagueColor = (lg) => {
    const idx = leagues.indexOf(lg);
    return LEAGUE_PALETTE[(idx - 1 + LEAGUE_PALETTE.length) % LEAGUE_PALETTE.length];
  };

  const prevDay = () => {
    const d = new Date(date + 'T12:00:00');
    d.setDate(d.getDate() - 1);
    setDate(fmt.isoDate(d));
    setLeague('all');
  };
  const nextDay = () => {
    const d = new Date(date + 'T12:00:00');
    d.setDate(d.getDate() + 1);
    setDate(fmt.isoDate(d));
    setLeague('all');
  };

  return (
    <div>
      {/* ── Date controls ────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 12 }} className="fade-in s1">
        <button onClick={prevDay} style={navBtnStyle}>←</button>
        <input
          type="date" value={date}
          onChange={e => { setDate(e.target.value); setLeague('all'); }}
          style={{
            flex: 1,
            background: tokens.colors.surface2,
            border: `1px solid ${tokens.colors.border2}`,
            color: tokens.colors.text,
            padding: '6px 10px', fontSize: 12,
            fontFamily: tokens.fonts.mono,
          }}
        />
        <button onClick={nextDay} style={navBtnStyle}>→</button>
        <button onClick={() => { setDate(fmt.isoDate()); setLeague('all'); }} style={{ ...navBtnStyle, color: tokens.colors.green, borderColor: tokens.colors.green }}>
          Today
        </button>
      </div>

      {/* ── Counts inline ─────────────────────────────────────────── */}
      <div style={{ fontSize: 11, color: tokens.colors.muted, marginBottom: 10 }} className="fade-in s1">
        {filtered.length} fixture{filtered.length !== 1 ? 's' : ''}
        {league !== 'all' && ` · ${leagues.length - 1} league${leagues.length - 2 !== 1 ? 's' : ''} total`}
      </div>

      {/* ── League chips ─────────────────────────────────────────── */}
      <div style={{
        display: 'flex', gap: 6,
        overflowX: 'auto', WebkitOverflowScrolling: 'touch',
        marginBottom: 12, paddingBottom: 2,
      }} className="fade-in s2">
        {leagues.map(l => (
          <button
            key={l}
            onClick={() => setLeague(l)}
            style={{
              flexShrink: 0,
              padding: '5px 10px', fontSize: 9,
              letterSpacing: '.1em', textTransform: 'uppercase',
              border: `1px solid ${league === l ? tokens.colors.green : tokens.colors.border2}`,
              background: league === l ? tokens.colors.greenDim : 'transparent',
              color: league === l ? tokens.colors.green : tokens.colors.muted,
              cursor: 'pointer',
              WebkitTapHighlightColor: 'transparent',
            }}
          >{l === 'all' ? 'All' : l}</button>
        ))}
      </div>

      {/* ── Fixture rows ─────────────────────────────────────────── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }} className="fade-in s3">
        {loading && <div style={{ color: tokens.colors.muted, fontSize: 12, padding: '8px 0' }}>Loading…</div>}
        {!loading && filtered.length === 0 && (
          <div style={{ color: tokens.colors.muted, fontSize: 12, padding: '8px 0' }}>No fixtures found.</div>
        )}
        {filtered.map((f, i) => {
          const accent = leagueColor(f.league);
          return (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '10px 12px',
              background: tokens.colors.surface,
              border: `1px solid ${tokens.colors.border}`,
              borderLeft: `3px solid ${accent}`,
            }}>
              <div style={{ fontSize: 12, fontWeight: 500, color: tokens.colors.muted, flexShrink: 0, minWidth: 44 }}>
                {f.kickoff ? fmt.time(f.kickoff) : '—'}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {f.home} <span style={{ color: tokens.colors.dim }}>vs</span> {f.away}
                </div>
                <div style={{ fontSize: 10, color: tokens.colors.muted, letterSpacing: '.08em', marginTop: 2 }}>
                  {f.league}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const navBtnStyle = {
  padding: '6px 10px', fontSize: 12,
  border: `1px solid ${tokens.colors.border2}`,
  background: 'transparent',
  color: tokens.colors.muted,
  cursor: 'pointer',
  fontFamily: 'inherit',
  WebkitTapHighlightColor: 'transparent',
};
