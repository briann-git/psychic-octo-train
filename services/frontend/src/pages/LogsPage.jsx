import { useState, useCallback } from 'react';
import tokens from '../tokens';
import Card from '../components/primitives/Card';
import SectionTitle from '../components/primitives/SectionTitle';
import Pulse from '../components/primitives/Pulse';
import useApi from '../hooks/useApi';
import useSSE from '../hooks/useSSE';
import { fetchLogs } from '../api/endpoints';

const LEVELS = ['all', 'INFO', 'WARN', 'ERROR'];

const LEVEL_COLOR = {
  INFO:  tokens.colors.blue,
  WARN:  tokens.colors.amber,
  ERROR: tokens.colors.red,
};

export default function LogsPage() {
  const [level, setLevel] = useState('all');
  const [useStream, setUseStream] = useState(true);

  const { data: staticLogs, loading } = useApi(
    useCallback(() => fetchLogs({ limit: 200 }), []),
    { interval: 0, enabled: !useStream }
  );
  const { lines: streamLines, connected } = useSSE('/api/logs/stream');

  const rawLines = useStream ? streamLines : (staticLogs || []);
  const filtered = level === 'all' ? rawLines : rawLines.filter(l => l.level === level);

  return (
    <div>
      <SectionTitle>Logs</SectionTitle>

      <div style={{ display: 'flex', gap: 6, marginBottom: 16, alignItems: 'center' }} className="fade-in s1">
        {LEVELS.map(l => (
          <div key={l} onClick={() => setLevel(l)} style={{
            padding: '4px 10px', fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase',
            border: `1px solid ${level === l ? tokens.colors.green : tokens.colors.border2}`,
            background: level === l ? tokens.colors.greenDim : 'transparent',
            color: level === l ? tokens.colors.green : tokens.colors.muted,
            cursor: 'pointer',
          }}>{l}</div>
        ))}
        <div
          onClick={() => setUseStream(s => !s)}
          style={{
            padding: '4px 10px', fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase',
            border: `1px solid ${useStream ? tokens.colors.green : tokens.colors.border2}`,
            background: useStream ? tokens.colors.greenDim : 'transparent',
            color: useStream ? tokens.colors.green : tokens.colors.muted,
            cursor: 'pointer',
          }}
        >
          {useStream ? 'Stream' : 'Poll'}
        </div>
        <div style={{ marginLeft: 'auto', fontSize: 10, color: tokens.colors.muted, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Pulse color={connected ? tokens.colors.green : tokens.colors.red} />
          {useStream ? (connected ? 'Live' : 'Reconnecting…') : 'Static'}
        </div>
      </div>

      <Card className="fade-in s2" style={{ padding: 0 }}>
        <div style={{ background: '#080808', padding: 16, fontFamily: tokens.fonts.mono, fontSize: 12, lineHeight: 2, maxHeight: 600, overflowY: 'auto' }}>
          {loading && !useStream && <div style={{ color: tokens.colors.muted }}>Loading…</div>}
          {!filtered.length && !loading && <div style={{ color: tokens.colors.muted }}>No log entries.</div>}
          {filtered.map((l, i) => (
            <div key={i} style={{ display: 'flex', gap: 14, borderBottom: `1px solid ${tokens.colors.border}`, padding: '4px 0' }}>
              <span style={{ color: tokens.colors.dim, flexShrink: 0, fontSize: 11 }}>{l.time}</span>
              <span style={{ flexShrink: 0, width: 40, fontSize: 11, color: LEVEL_COLOR[l.level] || tokens.colors.muted }}>{l.level}</span>
              <span style={{ color: tokens.colors.muted, flexShrink: 0, minWidth: 80, fontSize: 11 }}>{l.source}</span>
              <span style={{ color: tokens.colors.text }}>{l.message}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
