import { useState } from 'react';
import { Outlet, useOutletContext } from 'react-router';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ListRow,
  ListSkeleton,
  Switch,
  useToast,
} from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { useAsync, useMutation } from '@shared/hooks';
import { cameras as camerasApi } from '../../api/client';
import type { Camera } from '../../api/types';
import { useCompanyId } from '../../app/SessionProvider';
import { LinkButton } from '../../components/LinkButton';
import { ConfirmDelete } from '../../components/forms/ConfirmDelete';
import type { CamerasOutletContext } from '../../components/forms/CameraForm';
import type { UnitOutletContext } from '../UnitDetailPage';

export function CamerasTab() {
  const t = useT();
  const toast = useToast();
  const companyId = useCompanyId();
  const { unitId } = useOutletContext<UnitOutletContext>();
  const [showInactive, setShowInactive] = useState(false);
  const cameras = useAsync(
    () => camerasApi.list(companyId, unitId, showInactive),
    [companyId, unitId, showInactive],
  );
  const remove = useMutation((id: string) => camerasApi.remove(companyId, id));
  const [pendingDelete, setPendingDelete] = useState<Camera | null>(null);
  const [togglingIds, setTogglingIds] = useState<ReadonlySet<string>>(new Set());

  async function toggleActive(camera: Camera, next: boolean) {
    if (togglingIds.has(camera.id)) return;
    setTogglingIds(ids => new Set(ids).add(camera.id));
    try {
      await camerasApi.update(companyId, camera.id, { is_active: next });
      toast.success(next ? t('Câmera ativada.') : t('Câmera desativada.'));
      cameras.setData(list => list?.map(c => (c.id === camera.id ? { ...c, is_active: next } : c)) ?? list);
      if (!showInactive && !next) void cameras.reload();
    } catch (error) {
      toast.error(localizeApiError(error, t));
    } finally {
      setTogglingIds(ids => {
        const copy = new Set(ids);
        copy.delete(camera.id);
        return copy;
      });
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    const result = await remove.run(pendingDelete.id);
    if (!result.ok) {
      toast.error(localizeApiError(result.error, t));
      return;
    }
    toast.success(t('Câmera excluída.'));
    setPendingDelete(null);
    void cameras.reload();
  }

  const outletContext: CamerasOutletContext = { unitId, reload: cameras.reload };

  return (
    <>
      <div className="argus-tab-toolbar">
        <Switch size="sm" label={t('Mostrar inativas')} checked={showInactive} onChange={setShowInactive} />
        <LinkButton to="new" size="sm">
          {t('Nova câmera')}
        </LinkButton>
      </div>
      <Card>
        {cameras.loading && !cameras.data ? (
          <ListSkeleton rows={3} label={t('Carregando')} />
        ) : cameras.error ? (
          <EmptyState
            title={t('Não foi possível carregar.')}
            description={localizeApiError(cameras.error, t)}
            action={
              <Button variant="secondary" size="sm" onClick={() => void cameras.reload()}>
                {t('Tentar novamente')}
              </Button>
            }
          />
        ) : !cameras.data || cameras.data.length === 0 ? (
          <EmptyState
            title={t('Nenhuma câmera ainda')}
            description={t('Adicione uma câmera com a URL RTSP do stream.')}
            action={<LinkButton to="new" size="sm">{t('Nova câmera')}</LinkButton>}
          />
        ) : (
          cameras.data.map(camera => (
            <ListRow
              key={camera.id}
              title={camera.name}
              meta={camera.stream_url || '—'}
              actions={
                <>
                  <Badge variant={camera.is_active ? 'normal' : 'neutral'}>
                    {camera.is_active ? t('Ativa') : t('Inativa')}
                  </Badge>
                  <Switch
                    size="sm"
                    hideLabel
                    label={t('Câmera ativa')}
                    checked={camera.is_active}
                    loading={togglingIds.has(camera.id)}
                    onChange={next => void toggleActive(camera, next)}
                  />
                  <LinkButton to={`${camera.id}/edit`} variant="ghost" size="sm">
                    {t('Editar')}
                  </LinkButton>
                  <Button size="sm" variant="danger" onClick={() => setPendingDelete(camera)}>
                    {t('Excluir')}
                  </Button>
                </>
              }
            />
          ))
        )}
      </Card>
      <Outlet context={outletContext} />
      <ConfirmDelete
        open={Boolean(pendingDelete)}
        busy={remove.pending}
        title={t('Excluir câmera')}
        name={pendingDelete?.name ?? ''}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setPendingDelete(null)}
      />
    </>
  );
}
