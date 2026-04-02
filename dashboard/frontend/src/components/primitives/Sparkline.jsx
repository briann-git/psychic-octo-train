import tokens from '../../tokens';

export default function Sparkline({ data, color = tokens.colors.green, negColor = tokens.colors.red }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height: 32, marginTop: 10 }}>
      {data.map((v, i) => (
        <div key={i} style={{
          flex: 1,
          height: `${Math.max(Math.abs(v), 2)}%`,
          background: v >= 0 ? `${color}22` : `${negColor}22`,
          borderTop: `1px solid ${v >= 0 ? color : negColor}`,
        }} />
      ))}
    </div>
  );
}
