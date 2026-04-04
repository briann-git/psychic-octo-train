import { useCallback } from 'react';
import tokens from '../tokens';
import Card from '../components/primitives/Card';
import CardTitle from '../components/primitives/CardTitle';
import SectionTitle from '../components/primitives/SectionTitle';
import useApi from '../hooks/useApi';
import useTimezone from '../hooks/useTimezone';
import { fetchConfig, fetchQuota } from '../api/endpoints';

const CONFIG_KEYS = [
  'CONFIDENCE_THRESHOLD', 'FLAT_STAKE', 'MIN_LEAD_HOURS', 'MAX_LEAD_HOURS',
  'LOG_LEVEL', 'BACKUP_HOUR', 'MORNING_HOUR',
  'RUN_INTERVAL_HOURS', 'MAX_ANALYSIS_LEAD_HOURS',
  'CALENDAR_LOOKAHEAD_DAYS', 'CALENDAR_REFRESH_HOUR',
];

const COMMON_TIMEZONES = [
  'UTC',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Europe/Madrid',
  'Europe/Rome',
  'Europe/Amsterdam',
  'Europe/Istanbul',
  'Africa/Nairobi',
  'Africa/Cairo',
  'Africa/Lagos',
  'Asia/Dubai',
  'Asia/Kolkata',
  'Asia/Shanghai',
  'Asia/Tokyo',
  'Australia/Sydney',
  'Pacific/Auckland',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Sao_Paulo',
];

function OddsApiQuota({ quota }) {
  if (!quota) {
    return (
      <div style={{ fontSize: 12, color: tokens.colors.muted }}>Loading…</div>
    );
  }

  const { remaining, used, last, updated_at } = quota;

  if (remaining === null && used === null) {
    return (
      <>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 8 }}>
          <span style={{ color: tokens.colors.muted }}>Odds API</span>
          <span style={{ color: tokens.colors.muted, fontSize: 11 }}>No data yet</span>
        </div>
        <div style={{ height: 6, background: tokens.colors.border }} />
        <div style={{ fontSize: 10, color: tokens.colors.muted, marginTop: 6 }}>
          Quota is captured from the next API call
        </div>
      </>
    );
  }

  const total = remaining + used;
  const pct = total > 0 ? (remaining / total) * 100 : 0;
  const barColor = pct > 30 ? tokens.colors.green : pct > 10 ? tokens.colors.amber : tokens.colors.red;

  const updatedLabel = updated_at
    ? new Date(updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : null;

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 8 }}>
        <span style={{ color: tokens.colors.muted }}>Odds API</span>
        <span style={{ color: barColor, fontFamily: tokens.fonts.mono }}>
          {remaining.toLocaleString()} remaining
        </span>
      </div>
      <div style={{ height: 6, background: tokens.colors.border, borderRadius: 3 }}>
        <div style={{ height: '100%', width: `${pct}%`, background: barColor, borderRadius: 3, transition: 'width 0.4s' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: tokens.colors.muted, marginTop: 6 }}>
        <span>{used.toLocaleString()} used · {last != null ? `last call: ${last}` : ''}</span>
        {updatedLabel && <span>as of {updatedLabel}</span>}
      </div>
    </>
  );
}


export default function SystemPage({ profiles }) {
  const { data: config, loading } = useApi(fetchConfig, { interval: 0 });
  const fetchQuotaCb = useCallback(fetchQuota, []);
  const { data: quota } = useApi(fetchQuotaCb, { interval: 60000 });
  const { tz, setTimezone, fmt } = useTimezone();
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
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: `1px solid ${tokens.colors.border}`, fontSize: 12 }}>
                <span style={{ color: tokens.colors.muted }}>Log Level</span>
                <span style={{ color: tokens.colors.text }}>{config.LOG_LEVEL || 'INFO'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', fontSize: 12 }}>
                <span style={{ color: tokens.colors.muted }}>Display Timezone</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontSize: 10, color: tokens.colors.amber }}>{fmt.label()}</span>
                  <select
                    value={tz}
                    onChange={e => setTimezone(e.target.value)}
                    style={{
                      background: tokens.colors.surface2, border: `1px solid ${tokens.colors.border2}`,
                      color: tokens.colors.text, padding: '3px 6px', fontSize: 11,
                      fontFamily: tokens.fonts.mono, cursor: 'pointer',
                    }}
                  >
                    {COMMON_TIMEZONES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
                  </select>
                </div>
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
              <OddsApiQuota quota={quota} />
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
