import { useState, useCallback } from 'react';
import tokens from '../tokens';
import Card from '../components/primitives/Card';
import SectionTitle from '../components/primitives/SectionTitle';
import useApi from '../hooks/useApi';
import useTimezone from '../hooks/useTimezone';
import { fetchFixtures } from '../api/endpoints';

export default function FixturesPage() {
  const { fmt } = useTimezone();
  const [league, setLeague] = useState('all');
  const [date, setDate] = useState(() => fmt.isoDate());
  const { data, loading } = useApi(useCallback(() => fetchFixtures({ date }), [date]), { interval: 60000 });

  const fixtures = data || [];
  const leagues  = ['all', ...Array.from(new Set(fixtures.map(f => f.league))).sort()];
  const filtered = league === 'all' ? fixtures : fixtures.filter(f => f.league === league);

  const todayCount = fixtures.length;

  return (
    <div>
      <SectionTitle>Fixtures</SectionTitle>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12, marginBottom: 16 }} className="fade-in s1">
        {[
          { label: 'Fixtures on Date',  value: fixtures.length,  color: tokens.colors.text },
          { label: 'Filtered',          value: filtered.length,  color: tokens.colors.blue },
          { label: 'Leagues',           value: leagues.length - 1, color: tokens.colors.green },
        ].map(({ label, value, color }) => (
          <Card key={label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 9, color: tokens.colors.muted, letterSpacing: '.15em', textTransform: 'uppercase', marginBottom: 8 }}>{label}</div>
            <div style={{ fontSize: 28, fontWeight: 500, color }}>{value}</div>
          </Card>
        ))}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }} className="fade-in s2">
        <div onClick={() => { const d = new Date(date + 'T12:00:00'); d.setDate(d.getDate() - 1); setDate(fmt.isoDate(d)); setLeague('all'); }}
          style={{ padding: '4px 10px', fontSize: 11, border: `1px solid ${tokens.colors.border2}`, color: tokens.colors.muted, cursor: 'pointer' }}>←</div>
        <input type="date" value={date} onChange={e => { setDate(e.target.value); setLeague('all'); }}
          style={{ background: tokens.colors.surface2, border: `1px solid ${tokens.colors.border2}`, color: tokens.colors.text, padding: '4px 10px', fontSize: 11, fontFamily: tokens.fonts.mono }} />
        <div onClick={() => { const d = new Date(date + 'T12:00:00'); d.setDate(d.getDate() + 1); setDate(fmt.isoDate(d)); setLeague('all'); }}
          style={{ padding: '4px 10px', fontSize: 11, border: `1px solid ${tokens.colors.border2}`, color: tokens.colors.muted, cursor: 'pointer' }}>→</div>
        <div onClick={() => { setDate(fmt.isoDate()); setLeague('all'); }}
          style={{ padding: '4px 10px', fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', border: `1px solid ${tokens.colors.border2}`, color: tokens.colors.green, cursor: 'pointer' }}>Today</div>
      </div>

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 16 }} className="fade-in s3">
        {leagues.map(l => (
          <div key={l} onClick={() => setLeague(l)} style={{
            padding: '4px 10px', fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase',
            border: `1px solid ${league === l ? tokens.colors.green : tokens.colors.border2}`,
            background: league === l ? tokens.colors.greenDim : 'transparent',
            color: league === l ? tokens.colors.green : tokens.colors.muted,
            cursor: 'pointer', transition: 'all .15s',
          }}>{l}</div>
        ))}
      </div>

      <Card className="fade-in s4">
        {loading && <div style={{ color: tokens.colors.muted, fontSize: 12 }}>Loading…</div>}
        {!loading && !filtered.length && <div style={{ color: tokens.colors.muted, fontSize: 12 }}>No fixtures found.</div>}
        {filtered.length > 0 && (
          <table>
            <thead>
              <tr><th>League</th><th>Home</th><th>Away</th><th>Kickoff</th></tr>
            </thead>
            <tbody>
              {filtered.map((f, i) => (
                <tr key={i}>
                  <td style={{ fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase', color: tokens.colors.muted }}>{f.league}</td>
                  <td>{f.home}</td>
                  <td>{f.away}</td>
                  <td style={{ color: tokens.colors.muted }}>
                    {f.kickoff ? fmt.dateTime(f.kickoff) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
