import tokens from '../../tokens';

export default function CardTitle({ children, action, onAction }) {
  return (
    <div style={{
      fontSize: tokens.fontSize.sm,
      letterSpacing: '.15em',
      textTransform: 'uppercase',
      color: tokens.colors.muted,
      marginBottom: 14,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    }}>
      <span>{children}</span>
      {action && (
        <span onClick={onAction} style={{ color: tokens.colors.blue, cursor: 'pointer', fontSize: tokens.fontSize.sm, letterSpacing: '.05em' }}>
          {action}
        </span>
      )}
    </div>
  );
}
