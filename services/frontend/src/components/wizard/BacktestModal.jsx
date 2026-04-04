import { useState } from 'react';
import { createPortal } from 'react-dom';
import tokens from '../../tokens';
import { runBacktest } from '../../api/endpoints';

const LEAGUES = [
  { id: 'EPL',              label: 'Premier League'   },
  { id: 'EFL_Championship', label: 'Championship'     },
  { id: 'Bundesliga1',      label: 'Bundesliga 1'     },
  { id: 'Bundesliga2',      label: 'Bundesliga 2'     },
  { id: 'Ligue1',           label: 'Ligue 1'          },
  { id: 'Ligue2',           label: 'Ligue 2'          },
  { id: 'La_Liga',          label: 'La Liga'          },
  { id: 'La_Liga2',         label: 'La Liga 2'        },
  { id: 'Serie_A',          label: 'Serie A'          },
  { id: 'Serie_B',          label: 'Serie B'          },
];

const tc    = tokens.colors.blue;
const tcDim = tokens.colors.blueDim;

const fieldStyle = {
  width: '100%', boxSizing: 'border-box',
  background: tokens.colors.surface2,
  border: `1px solid ${tokens.colors.border}`,
  color: tokens.colors.text,
  padding: '7px 10px', fontSize: 12,
  fontFamily: tokens.fonts.mono,
  outline: 'none',
};

const labelStyle = {
  display: 'block',
  fontSize: 10, letterSpacing: '.1em', textTransform: 'uppercase',
  color: tokens.colors.muted, marginBottom: 5,
};

export default function BacktestModal({ profile, open, onClose, onComplete }) {
  const [league,   setLeague]   = useState('EPL');
  const [season,   setSeason]   = useState('2526');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo,   setDateTo]   = useState('');
  const [running,  setRunning]  = useState(false);
  const [error,    setError]    = useState(null);

  const canRun = season.trim().length >= 4;

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    try {
      const body = { league, season: season.trim() };
      if (dateFrom) body.date_from = new Date(dateFrom).toISOString();
      if (dateTo)   body.date_to   = new Date(dateTo).toISOString();
      await runBacktest(profile.id, body);
      onComplete(profile.id);
    } catch (e) {
      setError(e.message || 'Backtest failed');
      setRunning(false);
    }
  };

  if (!open || !profile) return null;

  return createPortal(
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: 'rgba(0,0,0,0.72)', backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: 440,
          background: tokens.colors.bg,
          border: `1px solid ${tokens.colors.border}`,
          boxShadow: '0 8px 32px rgba(0,0,0,.6)',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '12px 20px', borderBottom: `1px solid ${tokens.colors.border}`,
        }}>
          <div style={{ fontSize: 11, letterSpacing: '.12em', textTransform: 'uppercase', color: tc }}>
            New Backtest — {profile.name}
          </div>
          <div
            onClick={running ? undefined : onClose}
            style={{ cursor: running ? 'not-allowed' : 'pointer', color: tokens.colors.dim, fontSize: 16, lineHeight: 1 }}
          >✕</div>
        </div>

        {/* Body */}
        <div style={{ padding: '20px 24px' }}>
          {running ? (
            <div style={{ textAlign: 'center', padding: '32px 0' }}>
              <div style={{ fontSize: 13, color: tc, marginBottom: 10, letterSpacing: '.05em' }}>
                Running backtest…
              </div>
              <div style={{ fontSize: 11, color: tokens.colors.muted, lineHeight: 1.8 }}>
                Replaying {league} {season} through your agents.<br />
                This may take a minute.
              </div>
            </div>
          ) : (
            <>
              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>League</label>
                <select value={league} onChange={e => setLeague(e.target.value)} style={fieldStyle}>
                  {LEAGUES.map(l => (
                    <option key={l.id} value={l.id}>{l.label}</option>
                  ))}
                </select>
              </div>

              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>Season</label>
                <input
                  value={season}
                  onChange={e => setSeason(e.target.value)}
                  placeholder="e.g. 2526"
                  style={fieldStyle}
                />
                <div style={{ marginTop: 4, fontSize: 10, color: tokens.colors.dim }}>
                  4-digit code — 2425 = 2024/25, 2526 = 2025/26
                </div>
              </div>

              <div style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Date from (optional)</label>
                  <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} style={fieldStyle} />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Date to (optional)</label>
                  <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} style={fieldStyle} />
                </div>
              </div>
            </>
          )}

          {error && (
            <div style={{
              marginTop: 4, marginBottom: 4, padding: '8px 10px', fontSize: 11,
              color: tokens.colors.red, border: `1px solid ${tokens.colors.red}`,
              background: tokens.colors.redDim,
            }}>
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        {!running && (
          <div style={{
            padding: '12px 24px', borderTop: `1px solid ${tokens.colors.border}`,
            display: 'flex', justifyContent: 'flex-end', gap: 8,
          }}>
            <div
              onClick={onClose}
              style={{
                padding: '7px 16px', fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase',
                cursor: 'pointer', border: `1px solid ${tokens.colors.border}`,
                color: tokens.colors.muted, background: tokens.colors.surface2,
              }}
            >Cancel</div>
            <div
              onClick={canRun ? handleRun : undefined}
              style={{
                padding: '7px 20px', fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase',
                cursor: canRun ? 'pointer' : 'not-allowed',
                border: `1px solid ${canRun ? tc : tokens.colors.border}`,
                color: canRun ? tc : tokens.colors.dim,
                background: canRun ? tcDim : tokens.colors.surface2,
              }}
            >Run</div>
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}

