import { useState } from 'react';
import tokens from '../tokens';
import Card from '../components/primitives/Card';
import CardTitle from '../components/primitives/CardTitle';
import SectionTitle from '../components/primitives/SectionTitle';
import useApi from '../hooks/useApi';
import { fetchConfig } from '../api/endpoints';

const TYPE_COLORS = {
  paper:    { fg: tokens.colors.amber, bg: tokens.colors.amberDim },
  live:     { fg: tokens.colors.green, bg: tokens.colors.greenDim },
  backtest: { fg: tokens.colors.cyan ?? '#67e8f9', bg: tokens.colors.cyanDim ?? 'rgba(103,232,249,.08)' },
};

export default function SettingsPage({ mode, profileId, profiles, activeProfile, switchProfile, createProfile, removeProfile, reloadProfiles }) {
  const { data: config, loading } = useApi(fetchConfig, { interval: 0 });
  const [newName, setNewName] = useState('');
  const [newType, setNewType] = useState('paper');
  const [newBankroll, setNewBankroll] = useState('1000');
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    await createProfile(newName.trim(), newType, parseFloat(newBankroll) || 1000);
    setNewName('');
    setNewBankroll('1000');
    setCreating(false);
  };

  const CONFIG_KEYS = [
    'CONFIDENCE_THRESHOLD', 'FLAT_STAKE', 'MIN_LEAD_HOURS', 'MAX_LEAD_HOURS',
    'LOG_LEVEL', 'BACKUP_HOUR', 'MORNING_HOUR', 'SNAPSHOT_HOUR',
    'ANALYSIS_HOUR', 'CALENDAR_LOOKAHEAD_DAYS', 'CALENDAR_REFRESH_HOUR',
  ];

  return (
    <div>
      <SectionTitle>Settings</SectionTitle>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }} className="fade-in s1">
        <Card>
          <CardTitle>Profiles</CardTitle>
          <div style={{ marginBottom: 16, fontSize: 12, color: tokens.colors.muted, lineHeight: 1.8 }}>
            Each profile isolates its own picks, agent states, and P&L. Switch between them anytime — the scheduler uses the active profile.
          </div>

          {/* Existing profiles */}
          <div style={{ marginBottom: 16 }}>
            {(profiles || []).map(p => {
              const tc = TYPE_COLORS[p.type] || TYPE_COLORS.paper;
              const isActive = activeProfile && p.id === activeProfile.id;
              return (
                <div key={p.id} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '8px 10px', marginBottom: 4,
                  border: `1px solid ${isActive ? tc.fg : tokens.colors.border}`,
                  background: isActive ? tc.bg : tokens.colors.surface,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {isActive && <div style={{ width: 6, height: 6, borderRadius: '50%', background: tc.fg, animation: 'pulse 1.5s infinite' }} />}
                    <span style={{ fontSize: 12, color: isActive ? tc.fg : tokens.colors.text }}>{p.name}</span>
                    <span style={{
                      fontSize: 9, letterSpacing: '.1em', textTransform: 'uppercase',
                      padding: '1px 5px', border: `1px solid ${tc.fg}`, color: tc.fg, background: tc.bg,
                    }}>{p.type}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    {!isActive && (
                      <span onClick={() => switchProfile(p.id)} style={{ fontSize: 11, cursor: 'pointer', color: tokens.colors.green, letterSpacing: '.05em' }}>Activate</span>
                    )}
                    {!isActive && (
                      <span onClick={() => removeProfile(p.id)} style={{ fontSize: 11, cursor: 'pointer', color: tokens.colors.red, letterSpacing: '.05em' }}>Delete</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Create new profile */}
          <div style={{ borderTop: `1px solid ${tokens.colors.border}`, paddingTop: 12 }}>
            <div style={{ fontSize: 11, letterSpacing: '.15em', textTransform: 'uppercase', color: tokens.colors.muted, marginBottom: 8 }}>New Profile</div>
            <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
              <input
                value={newName}
                onChange={e => setNewName(e.target.value)}
                placeholder="Name"
                style={{
                  flex: 1, padding: '6px 8px', fontSize: 12,
                  background: tokens.colors.surface2, border: `1px solid ${tokens.colors.border}`,
                  color: tokens.colors.text, outline: 'none',
                }}
              />
              <select
                value={newType}
                onChange={e => setNewType(e.target.value)}
                style={{
                  padding: '6px 8px', fontSize: 12,
                  background: tokens.colors.surface2, border: `1px solid ${tokens.colors.border}`,
                  color: tokens.colors.text, outline: 'none',
                }}
              >
                <option value="paper">Paper</option>
                <option value="live">Live</option>
                <option value="backtest">Backtest</option>
              </select>
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <input
                value={newBankroll}
                onChange={e => setNewBankroll(e.target.value)}
                placeholder="Bankroll"
                type="number"
                style={{
                  flex: 1, padding: '6px 8px', fontSize: 12,
                  background: tokens.colors.surface2, border: `1px solid ${tokens.colors.border}`,
                  color: tokens.colors.text, outline: 'none',
                }}
              />
              <div
                onClick={creating ? undefined : handleCreate}
                style={{
                  padding: '6px 14px', fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase',
                  cursor: creating || !newName.trim() ? 'not-allowed' : 'pointer',
                  background: tokens.colors.greenDim, border: `1px solid ${tokens.colors.green}`,
                  color: tokens.colors.green, opacity: creating || !newName.trim() ? 0.5 : 1,
                }}
              >
                {creating ? 'Creating…' : 'Create'}
              </div>
            </div>
          </div>

          {mode === 'live' && (
            <div style={{ marginTop: 12, padding: 12, border: `1px solid ${tokens.colors.red}`, background: tokens.colors.redDim, fontSize: 12, color: tokens.colors.red, lineHeight: 1.7 }}>
              ⚠ Live profile active. Real stakes will be placed. Ensure bookmaker API keys are configured and bankroll limits are set.
            </div>
          )}
        </Card>

        <Card>
          <CardTitle>Pipeline Config</CardTitle>
          {loading && <div style={{ color: tokens.colors.muted, fontSize: 12 }}>Loading…</div>}
          {config && CONFIG_KEYS.map(key => config[key] != null ? (
            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${tokens.colors.border}`, fontSize: 12 }}>
              <span style={{ color: tokens.colors.muted, fontFamily: tokens.fonts.mono, fontSize: 11 }}>{key}</span>
              <span style={{ color: tokens.colors.text }}>{config[key]}</span>
            </div>
          ) : null)}
        </Card>

        <Card>
          <CardTitle>System</CardTitle>
          {config && (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${tokens.colors.border}`, fontSize: 12 }}>
                <span style={{ color: tokens.colors.muted }}>DB Path</span>
                <span style={{ color: tokens.colors.text, fontSize: 10 }}>{config.DB_PATH}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${tokens.colors.border}`, fontSize: 12 }}>
                <span style={{ color: tokens.colors.muted }}>Active Profile</span>
                <span style={{ color: mode === 'live' ? tokens.colors.green : tokens.colors.amber }}>{activeProfile ? activeProfile.name : '—'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${tokens.colors.border}`, fontSize: 12 }}>
                <span style={{ color: tokens.colors.muted }}>Mode</span>
                <span style={{ color: mode === 'live' ? tokens.colors.green : tokens.colors.amber }}>{mode}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', fontSize: 12 }}>
                <span style={{ color: tokens.colors.muted }}>Log Level</span>
                <span style={{ color: tokens.colors.text }}>{config.LOG_LEVEL || 'INFO'}</span>
              </div>
            </>
          )}
        </Card>

        <Card>
          <CardTitle>API Quota</CardTitle>
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 8 }}>
              <span style={{ color: tokens.colors.muted }}>Football Data API</span>
              <span style={{ color: tokens.colors.green }}>Unlimited</span>
            </div>
            <div style={{ height: 6, background: tokens.colors.border }}>
              <div style={{ height: '100%', width: '100%', background: tokens.colors.green }} />
            </div>
            <div style={{ fontSize: 10, color: tokens.colors.muted, marginTop: 6 }}>CSV source — no request limits</div>
          </div>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 8 }}>
              <span style={{ color: tokens.colors.muted }}>Odds API</span>
              <span style={{ color: tokens.colors.text }}>See provider dashboard</span>
            </div>
            <div style={{ height: 6, background: tokens.colors.border }} />
          </div>
        </Card>
      </div>
    </div>
  );
}
