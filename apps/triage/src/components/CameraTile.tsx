import { Badge, Status } from '@argus/design-system';
import { useT } from '@argus/i18n';
import type { CameraOverview } from '../api';
import { useLatestFrame } from '../hooks/useLatestFrame';

interface CameraTileProps {
  accountId: string;
  camera: CameraOverview;
  openCount: number;
  /** This camera produced the focused / newest detection. */
  alert: boolean;
  focused: boolean;
  onSelect: () => void;
}

export function CameraTile({ accountId, camera, openCount, alert, focused, onSelect }: CameraTileProps) {
  const t = useT();
  const frame = useLatestFrame(accountId, camera.id);
  const live = frame.status === 'ok';
  const signalLabel = frame.status === 'loading' ? t('Carregando…') : live ? t('Ao vivo') : t('Sem sinal');
  const className = [
    'argus-cam-tile',
    alert ? 'argus-cam-tile--alert' : '',
    focused ? 'argus-cam-tile--focused' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      type="button"
      className={className}
      aria-pressed={focused}
      aria-label={`${camera.name} · ${signalLabel}${openCount ? ` · ${t('{count} casos abertos', { count: openCount })}` : ''}`}
      onClick={onSelect}
    >
      <span className="argus-cam-tile__media">
        {frame.url ? (
          <img src={frame.url} alt="" className={frame.status === 'ok' ? '' : 'argus-cam-tile__img--stale'} />
        ) : (
          <span className="argus-cam-tile__placeholder" aria-hidden="true">
            {signalLabel}
          </span>
        )}
      </span>
      <span className="argus-cam-tile__bar">
        <span className="argus-cam-tile__name">{camera.name}</span>
        <Status label={signalLabel} tone={live ? 'live' : frame.status === 'loading' ? 'neutral' : 'error'} />
        {openCount > 0 ? <Badge variant="open">{openCount}</Badge> : null}
      </span>
    </button>
  );
}
