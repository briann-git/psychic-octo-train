import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import tokens from '../../tokens';
import PRESETS from './presets';
import StepBasics from './StepBasics';
import StepAgents from './StepAgents';
import StepReview from './StepReview';

const STEPS = ['Basics', 'Agents', 'Review'];

const TYPE_COLORS = {
  paper: tokens.colors.amber,
  live: tokens.colors.green,
  backtest: tokens.colors.blue,
};

export default function ProfileWizard({ open, onClose, onCreate }) {
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [type, setType] = useState('paper');
  const [preset, setPreset] = useState('balanced');
  const [agents, setAgents] = useState(() => PRESETS.balanced.agents.map(a => ({ ...a })));
  const [creating, setCreating] = useState(false);

  // Reset when opened
  useEffect(() => {
    if (open) {
      setStep(0);
      setName('');
      setType('paper');
      setPreset('balanced');
      setAgents(PRESETS.balanced.agents.map(a => ({ ...a })));
      setCreating(false);
    }
  }, [open]);

  if (!open) return null;

  const tc = TYPE_COLORS[type] || tokens.colors.amber;

  const canNext = step === 0
    ? name.trim().length > 0
    : step === 1
    ? agents.length > 0 && agents.every(a => a.bankroll > 0)
    : true;

  const handleCreate = async () => {
    setCreating(true);
    try {
      await onCreate({ name: name.trim(), type, agents });
      onClose();
    } catch {
      setCreating(false);
    }
  };

  return createPortal(
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        background: 'rgba(0,0,0,0.72)', backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: 540, maxHeight: '90vh',
          display: 'flex', flexDirection: 'column',
          background: tokens.colors.bg, border: `1px solid ${tokens.colors.border}`,
          boxShadow: '0 8px 32px rgba(0,0,0,.6)',
        }}
      >
        {/* Step indicator */}
        <div style={{
          display: 'flex', alignItems: 'center', borderBottom: `1px solid ${tokens.colors.border}`,
          flexShrink: 0,
        }}>
          {STEPS.map((s, i) => (
            <div
              key={s}
              style={{
                flex: 1, padding: '12px 0', textAlign: 'center',
                fontSize: 11, letterSpacing: '.15em', textTransform: 'uppercase',
                color: i === step ? tc : tokens.colors.dim,
                borderBottom: i === step ? `2px solid ${tc}` : '2px solid transparent',
                transition: 'all .15s',
              }}
            >
              <span style={{ marginRight: 4, fontSize: 10 }}>{i + 1}.</span>{s}
            </div>
          ))}
          <div
            onClick={onClose}
            title="Cancel"
            style={{
              padding: '0 14px', fontSize: 16, lineHeight: 1, cursor: 'pointer',
              color: tokens.colors.dim, alignSelf: 'stretch',
              display: 'flex', alignItems: 'center',
              borderLeft: `1px solid ${tokens.colors.border}`,
              transition: 'color .15s',
            }}
            onMouseEnter={e => e.currentTarget.style.color = tokens.colors.text}
            onMouseLeave={e => e.currentTarget.style.color = tokens.colors.dim}
          >✕</div>
        </div>

        {/* Body */}
        <div style={{ padding: '20px 24px', overflowY: 'auto', flex: 1 }}>
          {step === 0 && (
            <StepBasics
              name={name} type={type}
              onNameChange={setName} onTypeChange={setType}
            />
          )}
          {step === 1 && (
            <StepAgents
              agents={agents} onAgentsChange={setAgents}
              preset={preset} onPresetChange={setPreset}
            />
          )}
          {step === 2 && (
            <StepReview name={name} type={type} agents={agents} />
          )}
        </div>

        {/* Footer */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', padding: '12px 24px',
          borderTop: `1px solid ${tokens.colors.border}`,
          flexShrink: 0,
        }}>
          <div>
            {step > 0 && (
              <div
                onClick={() => setStep(s => s - 1)}
                style={{
                  padding: '7px 16px', fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase',
                  cursor: 'pointer', border: `1px solid ${tokens.colors.border}`,
                  color: tokens.colors.muted, background: tokens.colors.surface2,
                }}
              >← Back</div>
            )}
          </div>

          <div>
            {step < 2 ? (
              <div
                onClick={canNext ? () => setStep(s => s + 1) : undefined}
                style={{
                  padding: '7px 16px', fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase',
                  cursor: canNext ? 'pointer' : 'not-allowed',
                  border: `1px solid ${canNext ? tc : tokens.colors.border}`,
                  color: canNext ? tc : tokens.colors.dim,
                  background: canNext ? `${tc}18` : tokens.colors.surface2,
                  opacity: canNext ? 1 : 0.5,
                }}
              >Next →</div>
            ) : (
              <div
                onClick={creating ? undefined : handleCreate}
                style={{
                  padding: '7px 20px', fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase',
                  cursor: creating ? 'wait' : 'pointer',
                  border: `1px solid ${type === 'live' ? tokens.colors.red : tokens.colors.green}`,
                  color: type === 'live' ? tokens.colors.red : tokens.colors.green,
                  background: type === 'live' ? tokens.colors.redDim : tokens.colors.greenDim,
                  opacity: creating ? 0.6 : 1,
                }}
              >{creating ? 'Creating…' : 'Create'}</div>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
