import { Button, EmptyState, GridSkeleton } from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import type { CameraOverview } from '../api';
import { CameraTile } from './CameraTile';

interface CameraGridProps {
  accountId: string;
  cameras: CameraOverview[] | null;
  loading: boolean;
  error: unknown;
  openCounts: ReadonlyMap<string, number>;
  alertCameraId: string | null;
  focusedCameraId: string | null;
  onRetry: () => void;
  onSelectCamera: (cameraId: string) => void;
}

export function CameraGrid({
  accountId,
  cameras,
  loading,
  error,
  openCounts,
  alertCameraId,
  focusedCameraId,
  onRetry,
  onSelectCamera,
}: CameraGridProps) {
  const t = useT();
  if (loading && !cameras) return <GridSkeleton tiles={6} label={t('Carregando')} />;
  if (error && !cameras) {
    return (
      <EmptyState
        title={t('Não foi possível carregar.')}
        description={localizeApiError(error, t)}
        action={
          <Button variant="secondary" size="sm" onClick={onRetry}>
            {t('Tentar novamente')}
          </Button>
        }
      />
    );
  }
  if (!cameras || cameras.length === 0) {
    return (
      <EmptyState
        title={t('Nenhuma câmera nesta unidade')}
        description={t('Cadastre câmeras na administração para vê-las aqui.')}
      />
    );
  }
  return (
    <div className="argus-cam-grid" role="list" aria-label={t('Câmeras')}>
      {cameras.map(camera => (
        <div key={camera.id} role="listitem">
          <CameraTile
            accountId={accountId}
            camera={camera}
            openCount={Math.max(camera.open_case_count, openCounts.get(camera.id) ?? 0)}
            alert={camera.id === alertCameraId}
            focused={camera.id === focusedCameraId}
            onSelect={() => onSelectCamera(camera.id)}
          />
        </div>
      ))}
    </div>
  );
}
