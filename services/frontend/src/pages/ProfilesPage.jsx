import { useState } from 'react';
import tokens from '../tokens';
import Card from '../components/primitives/Card';
import SectionTitle from '../components/primitives/SectionTitle';
import ProfileWizard from '../components/wizard/ProfileWizard';
import BacktestModal from '../components/wizard/BacktestModal';
import useApi from '../hooks/useApi';
import { fetchBacktestReports } from '../api/endpoints';

const TYPE_COLORS = {
  paper:    { fg: tokens.colors.amber, bg: tokens.colors.amberDim },
  live:     { fg: tokens.colors.green, bg: tokens.colors.greenDim },
  backtest: { fg: tokens.colors.blue,  bg: tokens.colors.blueDim  },
};

export default function ProfilesPage({ profiles, toggleActive, createProfile, removeProfile, selectProfile, setPage }) {
  const [wizardOpen, setWizardOpen] = useState(false);
  const [backtestProfile, setBacktestProfile] = useState(null);

  const { data: allReports, refetch: reloadReports } = useApi(fetchBacktestReports, { interval: 0 });
  const reportCountByProfile = (allReports || []).reduce((acc, r) => {
    acc[r.profile_id] = (acc[r.profile_id] || 0) + 1;
    return acc;
  }, {});

  const handleRunComplete = (profileId) => {
    reloadReports();
    setBacktestProfile(null);
    if (selectProfile) selectProfile(profileId);
    if (setPage) setPage('backtests');
  };

  return (
    <div>
      <SectionTitle>Profiles</SectionTitle>

      <div style={{ maxWidth: 640 }} className="fade-in s1">
        <div style={{ marginBottom: 16, fontSize: 12, color: tokens.colors.muted, lineHeight: 1.8 }}>
          Each profile isolates its own picks, agent states, and P&L.
          Active profiles are processed by the scheduler.
        </div>

        {(profiles || []).map(p => {
          const tc = TYPE_COLORS[p.type] || TYPE_COLORS.paper;
          const isActive = p.is_active;
          const reportCount = reportCountByProfile[p.id] || 0;
          return (
            <div key={p.id} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '10px 12px', marginBottom: 4,
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
                {reportCount > 0 && (
                  <span
                    onClick={() => { if (selectProfile) selectProfile(p.id); if (setPage) setPage('backtests'); }}
                    style={{
                      fontSize: 9, letterSpacing: '.08em', padding: '1px 6px', cursor: 'pointer',
                      border: `1px solid ${tokens.colors.blue}`, color: tokens.colors.blue,
                      background: tokens.colors.blueDim,
                    }}
                  >{reportCount} {reportCount === 1 ? 'backtest' : 'backtests'}</span>
                )}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <span
                  onClick={() => toggleActive(p.id)}
                  style={{ fontSize: 11, cursor: 'pointer', color: isActive ? tokens.colors.amber : tokens.colors.green, letterSpacing: '.05em' }}
                >{isActive ? 'Deactivate' : 'Activate'}</span>
                <span
                  onClick={() => setBacktestProfile(p)}
                  style={{ fontSize: 11, cursor: 'pointer', color: tokens.colors.blue, letterSpacing: '.05em' }}
                >Backtest</span>
                {!isActive && (
                  <span onClick={() => removeProfile(p.id)} style={{ fontSize: 11, cursor: 'pointer', color: tokens.colors.red, letterSpacing: '.05em' }}>Delete</span>
                )}
              </div>
            </div>
          );
        })}

        <div style={{ marginTop: 12 }}>
          <div
            onClick={() => setWizardOpen(true)}
            style={{
              padding: '8px 0', textAlign: 'center', fontSize: 11,
              letterSpacing: '.15em', textTransform: 'uppercase',
              cursor: 'pointer', border: `1px solid ${tokens.colors.border}`,
              color: tokens.colors.green, background: tokens.colors.greenDim,
            }}
          >+ New Profile</div>
        </div>

        <ProfileWizard
          open={wizardOpen}
          onClose={() => setWizardOpen(false)}
          onCreate={createProfile}
        />

        <BacktestModal
          profile={backtestProfile}
          open={!!backtestProfile}
          onClose={() => setBacktestProfile(null)}
          onComplete={handleRunComplete}
        />

        {(profiles || []).some(p => p.is_active && p.type === 'live') && (
          <div style={{ marginTop: 12, padding: 12, border: `1px solid ${tokens.colors.red}`, background: tokens.colors.redDim, fontSize: 12, color: tokens.colors.red, lineHeight: 1.7 }}>
            ⚠ A live profile is active. Real stakes will be placed. Ensure bookmaker API keys are configured and bankroll limits are set.
          </div>
        )}
      </div>
    </div>
  );
}
