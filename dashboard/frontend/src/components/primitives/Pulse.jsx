import tokens from '../../tokens';

export default function Pulse({ color = tokens.colors.green }) {
  return (
    <div style={{
      width: 7,
      height: 7,
      borderRadius: '50%',
      background: color,
      animation: 'pulse 2s ease-in-out infinite',
      flexShrink: 0,
    }} />
  );
}
