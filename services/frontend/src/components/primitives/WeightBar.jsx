import tokens from '../../tokens';

export default function WeightBar({ stat, mkt }) {
  return (
    <div style={{ marginTop: 10 }}>
      <div style={{ fontSize: tokens.fontSize.xs, color: tokens.colors.muted, marginBottom: 4, letterSpacing: '.08em' }}>
        STAT ← → MKT
      </div>
      <div style={{ height: 4, background: tokens.colors.border, position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${stat * 100}%`, background: tokens.colors.green, transition: 'width .5s' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: tokens.fontSize.xs, color: tokens.colors.muted, marginTop: 4 }}>
        <span>{(+stat).toFixed(2)}</span>
        <span>{(+mkt).toFixed(2)}</span>
      </div>
    </div>
  );
}
