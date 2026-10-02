interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  /** Accessible label. Omit when the parent already announces busy state (e.g. `Button loading`). */
  label?: string;
  className?: string;
}

/** Indeterminate progress ring. Rotates with `transform` only; honours reduced motion. */
export function Spinner({ size = 'sm', label, className }: SpinnerProps) {
  const classes = ['argus-spinner', `argus-spinner--${size}`, className].filter(Boolean).join(' ');
  if (!label) return <span className={classes} aria-hidden="true" />;
  return <span className={classes} role="status" aria-label={label} />;
}
