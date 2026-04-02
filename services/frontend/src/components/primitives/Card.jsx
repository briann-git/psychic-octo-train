import tokens from '../../tokens';

export default function Card({ children, style, className }) {
  return (
    <div className={className} style={{
      border: `1px solid ${tokens.colors.border}`,
      background: tokens.colors.surface,
      padding: tokens.spacing.lg,
      ...style,
    }}>
      {children}
    </div>
  );
}
