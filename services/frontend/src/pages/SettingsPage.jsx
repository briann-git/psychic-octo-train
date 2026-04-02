import tokens from '../tokens';
import Card from '../components/primitives/Card';
import CardTitle from '../components/primitives/CardTitle';
import SectionTitle from '../components/primitives/SectionTitle';
import useApi from '../hooks/useApi';
import { fetchConfig } from '../api/endpoints';

export default function SettingsPage({ mode, setMode }) {
  const { data: config, loading } = useApi(fetchConfig, { interval: 0 });

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
          <CardTitle>Trading Mode</CardTitle>
          <div style={{ marginBottom: 16, fontSize: 12, color: tokens.colors.muted, lineHeight: 1.8 }}>
            Paper trading runs the full pipeline with no real money. Live mode activates the execution layer and places real bets.
          </div>
          <div style={{ display: 'flex', gap: 0, marginBottom: 16 }}>
            {['paper', 'live'].map(m => (
              <div key={m} onClick={() => setMode(m)} style={{
                flex: 1, padding: '12px 0', textAlign: 'center',
                fontSize: 11, letterSpacing: '.15em', textTransform: 'uppercase',
                cursor: 'pointer',
                background: mode === m ? (m === 'paper' ? tokens.colors.amberDim : tokens.colors.greenDim) : tokens.colors.surface2,
                border: `1px solid ${mode === m ? (m === 'paper' ? tokens.colors.amber : tokens.colors.green) : tokens.colors.border2}`,
                color: mode === m ? (m === 'paper' ? tokens.colors.amber : tokens.colors.green) : tokens.colors.muted,
                transition: 'all .2s',
              }}>
                {m === 'live' && <span style={{ marginRight: 6 }}>⚡</span>}{m}
              </div>
            ))}
          </div>
          {mode === 'live' && (
            <div style={{ padding: 12, border: `1px solid ${tokens.colors.red}`, background: tokens.colors.redDim, fontSize: 12, color: tokens.colors.red, lineHeight: 1.7 }}>
              ⚠ Live mode active. Real stakes will be placed. Ensure bookmaker API keys are configured and bankroll limits are set.
            </div>
          )}
          {mode === 'paper' && (
            <div style={{ padding: 12, border: `1px solid ${tokens.colors.amber}`, background: tokens.colors.amberDim, fontSize: 12, color: tokens.colors.amber, lineHeight: 1.7 }}>
              Paper trading active. All picks are simulated — no real money at risk.
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
