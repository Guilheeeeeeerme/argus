import { useState } from 'react';
import { Link, Outlet } from 'react-router';
import {
  Button,
  Card,
  EmptyState,
  ListRow,
  ListSkeleton,
  PageHeader,
  useToast,
} from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { useAsync, useMutation } from '@shared/hooks';
import { units as unitsApi } from '../api/client';
import type { Unit } from '../api/types';
import { RequireAccount } from '../app/guards';
import { useAccountId, useSession } from '../app/SessionProvider';
import { LinkButton } from '../components/LinkButton';
import { ConfirmDelete } from '../components/forms/ConfirmDelete';
import type { UnitsOutletContext } from '../components/forms/UnitForm';

export function UnitsPage() {
  return (
    <RequireAccount>
      <UnitsList />
    </RequireAccount>
  );
}

function UnitsList() {
  const t = useT();
  const toast = useToast();
  const accountId = useAccountId();
  const { reloadContext } = useSession();
  const units = useAsync(() => unitsApi.list(accountId), [accountId]);
  const remove = useMutation((id: string) => unitsApi.remove(accountId, id));
  const [pendingDelete, setPendingDelete] = useState<Unit | null>(null);

  async function confirmDelete() {
    if (!pendingDelete) return;
    const result = await remove.run(pendingDelete.id);
    if (!result.ok) {
      toast.error(localizeApiError(result.error, t));
      return;
    }
    toast.success(t('Unidade excluída.'));
    setPendingDelete(null);
    void units.reload();
    void reloadContext();
  }

  const outletContext: UnitsOutletContext = { reload: units.reload };

  return (
    <>
      <PageHeader
        title={t('Unidades')}
        description={t('Lojas, salas ou campi desta conta. Cada unidade agrupa câmeras, instruções e webhooks.')}
        actions={<LinkButton to="new">{t('Nova unidade')}</LinkButton>}
      />
      <Card>
        {units.loading && !units.data ? (
          <ListSkeleton rows={4} label={t('Carregando')} />
        ) : units.error ? (
          <EmptyState
            title={t('Não foi possível carregar.')}
            description={localizeApiError(units.error, t)}
            action={
              <Button variant="secondary" size="sm" onClick={() => void units.reload()}>
                {t('Tentar novamente')}
              </Button>
            }
          />
        ) : !units.data || units.data.length === 0 ? (
          <EmptyState
            title={t('Nenhuma unidade ainda')}
            description={t('Adicione uma unidade para gerenciar câmeras e instruções.')}
            action={<LinkButton to="new" size="sm">{t('Nova unidade')}</LinkButton>}
          />
        ) : (
          units.data.map(unit => (
            <ListRow
              key={unit.id}
              title={<Link to={`/units/${unit.id}`}>{unit.name}</Link>}
              meta={`${unit.address || t('sem endereço')} · ${unit.timezone}`}
              actions={
                <>
                  <LinkButton to={`/units/${unit.id}/cameras`} variant="ghost" size="sm">
                    {t('Câmeras')}
                  </LinkButton>
                  <LinkButton to={`${unit.id}/edit`} variant="ghost" size="sm">
                    {t('Editar')}
                  </LinkButton>
                  <Button size="sm" variant="danger" onClick={() => setPendingDelete(unit)}>
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
        title={t('Excluir unidade')}
        name={pendingDelete?.name ?? ''}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setPendingDelete(null)}
      />
    </>
  );
}
