import { Skeleton } from './Skeleton';

interface PresetProps {
  label?: string;
}

/** Placeholder for a `ListRow` list while it loads. Never render `EmptyState` in that window. */
export function ListSkeleton({ rows = 4, label = 'Carregando' }: PresetProps & { rows?: number }) {
  return (
    <div className="argus-skeleton-list" role="status" aria-label={label}>
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="argus-skeleton-list__row" aria-hidden="true">
          <div className="argus-skeleton-list__main">
            <Skeleton width="40%" height={14} aria-label="" />
            <Skeleton width="65%" height={12} aria-label="" />
          </div>
          <Skeleton width={72} height={28} aria-label="" />
        </div>
      ))}
    </div>
  );
}

/** Placeholder for a card/tile grid (camera grid, overview counters). */
export function GridSkeleton({ tiles = 6, label = 'Carregando' }: PresetProps & { tiles?: number }) {
  return (
    <div className="argus-skeleton-grid" role="status" aria-label={label}>
      {Array.from({ length: tiles }, (_, index) => (
        <Skeleton key={index} width="100%" height={120} aria-label="" />
      ))}
    </div>
  );
}

/** Placeholder for a form while its record loads (edit drawers). */
export function FormSkeleton({ fields = 3, label = 'Carregando' }: PresetProps & { fields?: number }) {
  return (
    <div className="argus-skeleton-form" role="status" aria-label={label}>
      {Array.from({ length: fields }, (_, index) => (
        <div key={index} className="argus-skeleton-form__field" aria-hidden="true">
          <Skeleton width="30%" height={12} aria-label="" />
          <Skeleton width="100%" height={36} aria-label="" />
        </div>
      ))}
    </div>
  );
}
