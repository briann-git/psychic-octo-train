import tokens from '../../tokens';

const styles = {
  won:     { color: tokens.colors.green,  border: `1px solid ${tokens.colors.green}`,   background: tokens.colors.greenDim },
  lost:    { color: tokens.colors.red,    border: `1px solid ${tokens.colors.red}`,     background: tokens.colors.redDim },
  pending: { color: tokens.colors.amber,  border: `1px solid ${tokens.colors.amber}`,   background: tokens.colors.amberDim },
  paper:   { color: tokens.colors.blue,   border: `1px solid ${tokens.colors.blue}`,    background: tokens.colors.blueDim },
  live:    { color: tokens.colors.green,  border: `1px solid ${tokens.colors.green}`,   background: tokens.colors.greenDim },
  skip:    { color: tokens.colors.muted,  border: `1px solid ${tokens.colors.border2}`, background: 'transparent' },
  back:    { color: tokens.colors.green,  border: `1px solid ${tokens.colors.green}`,   background: tokens.colors.greenDim },
  error:   { color: tokens.colors.red,    border: `1px solid ${tokens.colors.red}`,     background: tokens.colors.redDim },
  info:    { color: tokens.colors.blue,   border: `1px solid ${tokens.colors.blue}`,    background: tokens.colors.blueDim },
  warn:    { color: tokens.colors.amber,  border: `1px solid ${tokens.colors.amber}`,   background: tokens.colors.amberDim },
};

export default function Badge({ type, children }) {
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 7px',
      fontSize: tokens.fontSize.sm,
      letterSpacing: '.08em',
      textTransform: 'uppercase',
      ...(styles[type] || styles.skip),
    }}>
      {children}
    </span>
  );
}
