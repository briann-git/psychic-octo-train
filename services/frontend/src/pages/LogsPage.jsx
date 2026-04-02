import { useState, useCallback, useRef, useEffect } from 'react';
import tokens from '../tokens';
import Card from '../components/primitives/Card';
import SectionTitle from '../components/primitives/SectionTitle';
import Pulse from '../components/primitives/Pulse';
import useApi from '../hooks/useApi';
import { fetchLogs } from '../api/endpoints';

const LEVELS = ['all', 'INFO', 'WARN', 'ERROR'];
const POLL_OPTIONS = [
  { label: '30s',  ms: 30_000 },
  { label: '1m',   ms: 60_000 },
  { label: '5m',   ms: 300_000 },
  { label: '15m',  ms: 900_000 },
];

const LEVEL_COLOR = {
  INFO:  tokens.colors.blue,
  WARN:  tokens.colors.amber,
  ERROR: tokens.colors.red,
};

export default function LogsPage() {
  const [level, setLevel] = useState('all');
  const [pollIdx, setPollIdx] = useState(0);
  const pollMs = POLL_OPTIONS[pollIdx].ms;
  const logEndRef = useRef(null);
  const containerRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);

  const { data, loading, error } = useApi(
    useCallback(() => fetchLogs({ limit: 200 }), []),
    { interval: pollMs }
  );

  const rawLines = data || [];
  const filtered = level === 'all' ? rawLines : rawLines.filter(l => l.level === level);

  const scrollToBottom = () => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Auto-scroll to bottom on initial load and when new data arrives (if autoScroll is on)
  useEffect(() => {
    if (autoScroll && filtered.length) scrollToBottom();
  }, [filtered, autoScroll]);

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setAutoScroll(atBottom);
  };

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

        <div style={{ width: 1, height: 20, background: tokens.colors.border2, margin: '0 4px' }} />

        {POLL_OPTIONS.map((opt, i) => (
          <div key={opt.label} onClick={() => setPollIdx(i)} style={{
            padding: '4px 10px', fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase',
            border: `1px solid ${pollIdx === i ? tokens.colors.green : tokens.colors.border2}`,
            background: pollIdx === i ? tokens.colors.greenDim : 'transparent',
            color: pollIdx === i ? tokens.colors.green : tokens.colors.muted,
            cursor: 'pointer',
          }}>{opt.label}</div>
        ))}

        <div style={{ width: 1, height: 20, background: tokens.colors.border2, margin: '0 4px' }} />

        <div onClick={scrollToBottom} style={{
          padding: '4px 10px', fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase',
          border: `1px solid ${tokens.colors.green}`,
          background: autoScroll ? tokens.colors.greenDim : 'transparent',
          color: tokens.colors.green,
          cursor: 'pointer',
        }}>▼ Live</div>

        <div style={{ marginLeft: 'auto', fontSize: 10, color: tokens.colors.muted, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Pulse color={error ? tokens.colors.red : tokens.colors.green} />
          {error ? 'Error' : `Polling every ${POLL_OPTIONS[pollIdx].label}`}
        </div>
      </div>

      <Card className="fade-in s2" style={{ padding: 0 }}>
        <div ref={containerRef} onScroll={handleScroll} style={{ background: '#080808', padding: 16, fontFamily: tokens.fonts.mono, fontSize: 12, lineHeight: 2, maxHeight: 600, overflowY: 'auto' }}>
          {loading && !rawLines.length && <div style={{ color: tokens.colors.muted }}>Loading…</div>}
          {!filtered.length && !loading && <div style={{ color: tokens.colors.muted }}>No log entries.</div>}
          {filtered.map((l, i) => (
            <div key={i} style={{ display: 'flex', gap: 14, borderBottom: `1px solid ${tokens.colors.border}`, padding: '4px 0' }}>
              <span style={{ color: tokens.colors.dim, flexShrink: 0, fontSize: 11 }}>{l.time}</span>
              <span style={{ flexShrink: 0, width: 40, fontSize: 11, color: LEVEL_COLOR[l.level] || tokens.colors.muted }}>{l.level}</span>
              <span style={{ color: tokens.colors.muted, flexShrink: 0, minWidth: 80, fontSize: 11 }}>{l.source}</span>
              <span style={{ color: tokens.colors.text }}>{l.message}</span>
            </div>
          ))}
          <div ref={logEndRef} />
        </div>
      </Card>
    </div>
  );
}
