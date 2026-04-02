import tokens from '../tokens';
import Card from '../components/primitives/Card';
import CardTitle from '../components/primitives/CardTitle';
import SectionTitle from '../components/primitives/SectionTitle';
import useApi from '../hooks/useApi';
import { fetchConfig } from '../api/endpoints';

const CONFIG_KEYS = [
  'CONFIDENCE_THRESHOLD', 'FLAT_STAKE', 'MIN_LEAD_HOURS', 'MAX_LEAD_HOURS',
  'LOG_LEVEL', 'BACKUP_HOUR', 'MORNING_HOUR', 'SNAPSHOT_HOUR',
  'ANALYSIS_HOUR', 'CALENDAR_LOOKAHEAD_DAYS', 'CALENDAR_REFRESH_HOUR',
];

export default function SystemPage({ profiles }) {
  const { data: config, loading } = useApi(fetchConfig, { interval: 0 });
  const activeCount = (profiles || []).filter(p => p.is_active).length;

  return (
    <div>
      <SectionTitle>System</SectionTitle>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }} className="fade-in s1">
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
          <CardTitle>Status</CardTitle>
          {config && (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${tokens.colors.border}`, fontSize: 12 }}>
                <span style={{ color: tokens.colors.muted }}>DB Path</span>
                <span style={{ color: tokens.colors.text, fontSize: 10 }}>{config.DB_PATH}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${tokens.colors.border}`, fontSize: 12 }}>
                <span style={{ color: tokens.colors.muted }}>Active Profiles</span>
                <span style={{ color: tokens.colors.green }}>{activeCount}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', fontSize: 12 }}>
                <span style={{ color: tokens.colors.muted }}>Log Level</span>
                <span style={{ color: tokens.colors.text }}>{config.LOG_LEVEL || 'INFO'}</span>
              </div>
            </>
          )}
        </Card>

        <Card style={{ gridColumn: '1 / -1' }}>
          <CardTitle>API Quota</CardTitle>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
            <div>
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
          </div>
        </Card>
      </div>
    </div>
  );
}
