import tokens from '../../tokens';

export default function AgentTag({ id }) {
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: 20,
      height: 20,
      fontSize: 11,
      fontWeight: 600,
      border: `1px solid ${tokens.colors.border2}`,
      background: tokens.colors.surface2,
      color: tokens.colors.text,
    }}>
      {id}
    </span>
  );
}
