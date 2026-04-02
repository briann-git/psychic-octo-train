import { useState, useEffect } from 'react';
import tokens from '../../tokens';
import Pulse from '../primitives/Pulse';

export default function Header({ mode, toggleMode, switching }) {
  const [time, setTime] = useState('');

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(now.toUTCString().split(' ')[4] + ' UTC');
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const modeColor = mode === 'paper' ? tokens.colors.amber : tokens.colors.green;
  const modeDim   = mode === 'paper' ? tokens.colors.amberDim : tokens.colors.greenDim;
  const modeGlow  = mode === 'paper' ? 'paperGlow' : 'liveGlow';

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
        <div
          onClick={switching ? undefined : toggleMode}
          style={{
            display: 'flex', alignItems: 'center', gap: tokens.spacing.sm,
            padding: '5px 14px',
            border: `1px solid ${modeColor}`,
            background: modeDim,
            cursor: switching ? 'wait' : 'pointer',
            animation: `${modeGlow} 3s ease-in-out infinite`,
            opacity: switching ? 0.6 : 1,
          }}
        >
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: modeColor, animation: 'pulse 1.5s infinite' }} />
          <span style={{ fontSize: tokens.fontSize.sm, letterSpacing: '.2em', textTransform: 'uppercase', color: modeColor, fontWeight: 600 }}>
            {mode === 'paper' ? 'Paper Trading' : '⚡ Live'}
          </span>
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
