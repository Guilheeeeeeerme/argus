import { Badge, Button, EmptyState, ListSkeleton, Status, badgeVariantForTriageState } from '@argus/design-system';
import { useT, triageStateLabel } from '@argus/i18n';
import type { TriageCase } from '../api';
import { caseTimestamp } from '../feed';
import type { SocketStatus } from '../hooks/useTriageSocket';

interface CaseRailProps {
  cases: TriageCase[];
  loading: boolean;
  focusId: string | null;
  newCount: number;
  connection: SocketStatus;
  onSelect: (id: string) => void;
  onShowNew: () => void;
}

function formatTime(item: TriageCase): string {
  const value = caseTimestamp(item);
  if (!value) return '--:--:--';
  return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function CaseRail({ cases, loading, focusId, newCount, connection, onSelect, onShowNew }: CaseRailProps) {
  const t = useT();
  const tone = connection === 'live' ? 'live' : connection === 'closed' ? 'error' : 'neutral';
  const label =
    connection === 'live'
      ? t('Ao vivo')
      : connection === 'reconnecting'
        ? t('Reconectando…')
        : connection === 'closed'
          ? t('Desconectado')
          : t('Conectando…');

  return (
    <aside className="argus-rail" aria-label={t('Fila de casos')}>
      <div className="argus-rail__head">
        <h2 className="argus-rail__title">{t('Fila de casos')}</h2>
        <Status label={label} tone={tone} />
      </div>
      {newCount > 0 ? (
        <Button size="sm" variant="secondary" className="argus-rail__pill" onClick={onShowNew}>
          {t('{count} novos', { count: newCount })}
        </Button>
      ) : null}
      {loading && cases.length === 0 ? (
        <ListSkeleton rows={4} label={t('Carregando casos')} />
      ) : cases.length === 0 ? (
        <EmptyState title={t('Nenhum caso ainda')} description={t('Novas detecções aparecerão aqui em tempo real.')} />
      ) : (
        <div className="argus-rail__list" role="list">
          {cases.map(item => {
            const active = item.id === focusId;
            return (
              <button
                key={item.id}
                type="button"
                role="listitem"
                className={['argus-rail-row', active ? 'argus-rail-row--active' : ''].filter(Boolean).join(' ')}
                aria-current={active ? 'true' : undefined}
                onClick={() => onSelect(item.id)}
              >
                <span className="argus-rail-row__time tabular-nums">{formatTime(item)}</span>
                <Badge variant={badgeVariantForTriageState(item.state)}>{triageStateLabel(item.state, t)}</Badge>
                <span className="argus-rail-row__label">
                  {item.detection?.camera_name || item.detection?.summary || item.id.slice(0, 8)}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </aside>
  );
}
