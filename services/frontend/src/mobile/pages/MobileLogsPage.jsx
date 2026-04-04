import { useState, useCallback, useRef, useEffect } from 'react';
import tokens from '../../tokens';
import Card from '../../components/primitives/Card';
import Pulse from '../../components/primitives/Pulse';
import useApi from '../../hooks/useApi';
import { fetchLogs } from '../../api/endpoints';

const LEVELS = ['all', 'INFO', 'WARN', 'ERROR'];
const POLL_OPTIONS = [
  { label: '30s', ms: 30_000 },
  { label: '1m',  ms: 60_000 },
  { label: '5m',  ms: 300_000 },
  { label: '15m', ms: 900_000 },
];
const LEVEL_COLOR = {
  INFO:  tokens.colors.blue,
  WARN:  tokens.colors.amber,
  ERROR: tokens.colors.red,
};

export default function MobileLogsPage() {
  const [level, setLevel]     = useState('all');
  const [pollIdx, setPollIdx] = useState(0);
  const pollMs    = POLL_OPTIONS[pollIdx].ms;
  const logEndRef = useRef(null);
  const containerRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);

  const { data, loading, error } = useApi(
    useCallback(() => fetchLogs({ limit: 200 }), []),
    { interval: pollMs }
  );

  const rawLines = data || [];
  const filtered = level === 'all' ? rawLines : rawLines.filter(l => l.level === level);

  useEffect(() => {
    if (autoScroll && filtered.length) {
      logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [filtered, autoScroll]);

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setAutoScroll(atBottom);
  };

  const chipStyle = (active) => ({
    flexShrink: 0,
    padding: '5px 10px', fontSize: 9,
    letterSpacing: '.1em', textTransform: 'uppercase',
    border: `1px solid ${active ? tokens.colors.green : tokens.colors.border2}`,
    background: active ? tokens.colors.greenDim : 'transparent',
    color: active ? tokens.colors.green : tokens.colors.muted,
    cursor: 'pointer',
    fontFamily: 'inherit',
    WebkitTapHighlightColor: 'transparent',
  });

  return (
    <div>
      {/* ── Level filter chips ───────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }} className="fade-in s1">
        {LEVELS.map(l => (
          <button key={l} onClick={() => setLevel(l)} style={chipStyle(level === l)}>{l}</button>
        ))}
      </div>

      {/* ── Poll interval chips ──────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12, alignItems: 'center' }} className="fade-in s1">
        <span style={{ fontSize: 9, color: tokens.colors.dim, letterSpacing: '.1em', textTransform: 'uppercase' }}>Refresh</span>
        {POLL_OPTIONS.map((opt, i) => (
          <button key={opt.label} onClick={() => setPollIdx(i)} style={chipStyle(pollIdx === i)}>{opt.label}</button>
        ))}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 5 }}>
          {loading && <Pulse color={tokens.colors.blue} />}
          {error && <span style={{ fontSize: 9, color: tokens.colors.red }}>Error</span>}
        </div>
      </div>

      {/* ── Log output ───────────────────────────────────────────── */}
      <Card style={{ padding: 0 }} className="fade-in s2">
        <div
          ref={containerRef}
          onScroll={handleScroll}
          style={{
            height: 'calc(100dvh - 280px)',
            overflowY: 'auto',
            overflowX: 'hidden',
            fontFamily: tokens.fonts.mono,
            fontSize: 11,
            lineHeight: 1.6,
            padding: '8px 10px',
            WebkitOverflowScrolling: 'touch',
          }}
        >
          {!filtered.length && !loading && (
            <div style={{ color: tokens.colors.muted }}>No log entries.</div>
          )}
          {filtered.map((line, i) => {
            const color = LEVEL_COLOR[line.level] || tokens.colors.muted;
            return (
              <div key={i} style={{ display: 'flex', gap: 8, paddingBottom: 2 }}>
                <span style={{ color, flexShrink: 0, fontSize: 9, marginTop: 2 }}>{line.level || 'LOG'}</span>
                <span style={{ color: tokens.colors.dim, flexShrink: 0 }}>{line.timestamp?.slice(11, 19) || ''}</span>
                <span style={{ color: tokens.colors.text, wordBreak: 'break-all' }}>{line.message}</span>
              </div>
            );
          })}
          <div ref={logEndRef} />
        </div>

        {/* Auto-scroll indicator */}
        {!autoScroll && (
          <button
            onClick={() => { setAutoScroll(true); logEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }}
            style={{
              width: '100%', padding: '6px 0',
              background: tokens.colors.surface2,
              border: 'none',
              borderTop: `1px solid ${tokens.colors.border}`,
              color: tokens.colors.green, fontSize: 10,
              letterSpacing: '.1em', textTransform: 'uppercase',
              cursor: 'pointer', fontFamily: 'inherit',
            }}
          >
            ↓ Jump to latest
          </button>
        )}
      </Card>
    </div>
  );
}
