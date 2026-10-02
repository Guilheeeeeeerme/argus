interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  className?: string;
  /** Pass an empty string when a parent preset already announces loading. */
  'aria-label'?: string;
}

export function Skeleton({
  width = '100%',
  height = 16,
  className,
  'aria-label': ariaLabel = 'Carregando',
}: SkeletonProps) {
  const classes = ['argus-skeleton', className].filter(Boolean).join(' ');
  if (!ariaLabel) return <span className={classes} style={{ width, height }} aria-hidden="true" />;
  return <span className={classes} style={{ width, height }} role="status" aria-label={ariaLabel} />;
}
