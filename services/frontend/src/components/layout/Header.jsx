import { useState, useEffect, useRef } from 'react';
import tokens from '../../tokens';
import Pulse from '../primitives/Pulse';

const TYPE_COLORS = {
  paper:    { fg: tokens.colors.amber, bg: tokens.colors.amberDim, glow: 'paperGlow' },
  live:     { fg: tokens.colors.green, bg: tokens.colors.greenDim, glow: 'liveGlow' },
  backtest: { fg: tokens.colors.cyan ?? '#67e8f9', bg: tokens.colors.cyanDim ?? 'rgba(103,232,249,.08)', glow: 'paperGlow' },
};

export default function Header({ mode, profiles, activeProfile, switchProfile, switching }) {
  const [time, setTime] = useState('');
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(now.toUTCString().split(' ')[4] + ' UTC');
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);

  const tc = TYPE_COLORS[mode] || TYPE_COLORS.paper;

  return (
    <div style={{
      borderBottom: `1px solid ${tokens.colors.border}`,
      padding: `0 ${tokens.spacing.xl}px`,
      height: 52,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      background: tokens.colors.bg,
      position: 'sticky',
      top: 0,
      zIndex: 100,
      flexShrink: 0,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing.lg }}>
        <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '.2em', textTransform: 'uppercase', color: tokens.colors.green }}>
          Pipeline Ops
        </span>
        <span style={{ color: tokens.colors.dim }}>/</span>
        <span style={{ color: tokens.colors.muted, fontSize: 11, letterSpacing: '.05em' }}>brians-lab</span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing.lg }}>
        {/* Profile selector dropdown */}
        <div ref={ref} style={{ position: 'relative' }}>
          <div
            onClick={switching ? undefined : () => setOpen(o => !o)}
            style={{
              display: 'flex', alignItems: 'center', gap: tokens.spacing.sm,
              padding: '5px 14px',
              border: `1px solid ${tc.fg}`,
              background: tc.bg,
              cursor: switching ? 'wait' : 'pointer',
              animation: `${tc.glow} 3s ease-in-out infinite`,
              opacity: switching ? 0.6 : 1,
            }}
          >
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: tc.fg, animation: 'pulse 1.5s infinite' }} />
            <span style={{ fontSize: tokens.fontSize.sm, letterSpacing: '.2em', textTransform: 'uppercase', color: tc.fg, fontWeight: 600 }}>
              {activeProfile ? activeProfile.name : mode}
            </span>
            <span style={{ fontSize: 9, color: tc.fg, marginLeft: 2 }}>▾</span>
          </div>

          {open && (
            <div style={{
              position: 'absolute', right: 0, top: '100%', marginTop: 4,
              minWidth: 220, background: tokens.colors.surface, border: `1px solid ${tokens.colors.border}`,
              zIndex: 200, boxShadow: '0 4px 12px rgba(0,0,0,.5)',
            }}>
              {(profiles || []).map(p => {
                const ptc = TYPE_COLORS[p.type] || TYPE_COLORS.paper;
                const isActive = activeProfile && p.id === activeProfile.id;
                return (
                  <div
                    key={p.id}
                    onClick={() => { if (!isActive) { switchProfile(p.id); setOpen(false); } }}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      padding: '8px 12px', cursor: isActive ? 'default' : 'pointer',
                      background: isActive ? ptc.bg : 'transparent',
                      borderLeft: `3px solid ${isActive ? ptc.fg : 'transparent'}`,
                    }}
                  >
                    <span style={{ fontSize: 12, color: isActive ? ptc.fg : tokens.colors.text }}>{p.name}</span>
                    <span style={{
                      fontSize: 9, letterSpacing: '.1em', textTransform: 'uppercase',
                      padding: '2px 6px', border: `1px solid ${ptc.fg}`, color: ptc.fg, background: ptc.bg,
                    }}>{p.type}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: tokens.spacing.sm, padding: '5px 10px', border: `1px solid ${tokens.colors.green}`, background: tokens.colors.greenDim }}>
          <Pulse />
          <span style={{ fontSize: tokens.fontSize.sm, letterSpacing: '.15em', textTransform: 'uppercase', color: tokens.colors.green }}>Running</span>
        </div>

        <span style={{ fontSize: 11, color: tokens.colors.muted }}>{time}</span>
      </div>
    </div>
  );
}
