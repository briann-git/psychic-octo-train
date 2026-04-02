import tokens from '../../tokens';

export default function SectionTitle({ children }) {
  return (
    <div style={{
      fontSize: tokens.fontSize.sm,
      letterSpacing: '.2em',
      textTransform: 'uppercase',
      color: tokens.colors.muted,
      marginBottom: tokens.spacing.lg,
      marginTop: tokens.spacing.xs,
      display: 'flex',
      alignItems: 'center',
      gap: 10,
    }}>
      {children}
      <div style={{ flex: 1, height: 1, background: tokens.colors.border }} />
    </div>
  );
}
