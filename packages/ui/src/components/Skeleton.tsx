interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  className?: string;
  'aria-label'?: string;
}

export function Skeleton({
  width = '100%',
  height = 16,
  className,
  'aria-label': ariaLabel = 'Loading',
}: SkeletonProps) {
  return (
    <span
      className={['argus-skeleton', className].filter(Boolean).join(' ')}
      style={{ width, height }}
      role="status"
      aria-label={ariaLabel}
    />
  );
}
