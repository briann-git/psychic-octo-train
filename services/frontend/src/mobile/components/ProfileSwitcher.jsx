import { createPortal } from 'react-dom';
import tokens from '../../tokens';

const TYPE_COLORS = {
  paper:    tokens.colors.amber,
  live:     tokens.colors.green,
  backtest: '#67e8f9',
};

export default function ProfileSwitcher({ open, onClose, profiles, viewedProfile, selectProfile }) {
  if (!open) return null;

  const handleSelect = (id) => {
    selectProfile(id);
    onClose();
  };

  return createPortal(
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 200,
          background: 'rgba(0,0,0,0.55)',
        }}
      />

      {/* Bottom sheet */}
      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 201,
        background: tokens.colors.surface,
        borderTop: `1px solid ${tokens.colors.border}`,
        paddingBottom: 'env(safe-area-inset-bottom)',
      }}>
        {/* Handle + title */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 16px 10px',
          borderBottom: `1px solid ${tokens.colors.border}`,
        }}>
          <span style={{
            fontSize: 10, letterSpacing: '.18em', textTransform: 'uppercase',
            color: tokens.colors.muted,
          }}>
            Switch Profile
          </span>
          <span
            onClick={onClose}
            style={{ fontSize: 14, color: tokens.colors.dim, cursor: 'pointer', padding: '0 2px' }}
          >✕</span>
        </div>

        {/* Profile list */}
        <div style={{ maxHeight: '55vh', overflowY: 'auto' }}>
          {(profiles || []).map(p => {
            const tc = TYPE_COLORS[p.type] || tokens.colors.amber;
            const isViewed  = viewedProfile && p.id === viewedProfile.id;
            const isActive  = p.is_active;

            return (
              <div
                key={p.id}
                onClick={() => handleSelect(p.id)}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '13px 16px',
                  borderBottom: `1px solid ${tokens.colors.border}`,
                  background: isViewed ? `${tc}10` : 'transparent',
                  WebkitTapHighlightColor: 'transparent',
                  cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  {/* Active scheduler dot */}
                  <div style={{
                    width: 7, height: 7, borderRadius: '50%',
                    background: isActive ? tc : tokens.colors.border,
                    flexShrink: 0,
                  }} />
                  <div>
                    <div style={{
                      fontSize: 13,
                      color: isViewed ? tc : tokens.colors.text,
                      fontWeight: isViewed ? 600 : 400,
                    }}>
                      {p.name}
                    </div>
                    <div style={{ fontSize: 10, color: tokens.colors.dim, marginTop: 2, letterSpacing: '.05em' }}>
                      {p.type}{isActive ? ' · running' : ' · inactive'}
                    </div>
                  </div>
                </div>

                {isViewed && (
                  <span style={{ fontSize: 11, color: tc }}>✓</span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </>,
    document.body
  );
}
