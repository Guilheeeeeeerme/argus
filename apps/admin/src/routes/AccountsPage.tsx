import { useState } from 'react';
import { Outlet } from 'react-router';
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
import { accounts as accountsApi } from '../api/client';
import type { Account } from '../api/types';
import { RequirePlatform } from '../app/guards';
import { useSession } from '../app/SessionProvider';
import { LinkButton } from '../components/LinkButton';
import { ConfirmDelete } from '../components/forms/ConfirmDelete';
import type { AccountsOutletContext } from '../components/forms/AccountForm';

export function AccountsPage() {
  return (
    <RequirePlatform>
      <AccountsList />
    </RequirePlatform>
  );
}

function AccountsList() {
  const t = useT();
  const toast = useToast();
  const { session, reloadContext, switchAccount } = useSession();
  const accounts = useAsync(() => accountsApi.list(), []);
  const remove = useMutation((id: string) => accountsApi.remove(id));
  const [pendingDelete, setPendingDelete] = useState<Account | null>(null);

  async function confirmDelete() {
    if (!pendingDelete) return;
    const result = await remove.run(pendingDelete.id);
    if (!result.ok) {
      toast.error(localizeApiError(result.error, t));
      return;
    }
    toast.success(t('Conta excluída.'));
    const wasActive = session?.activeAccount?.id === pendingDelete.id;
    setPendingDelete(null);
    void accounts.reload();
    if (wasActive) void switchAccount(null);
    else void reloadContext();
  }

  const outletContext: AccountsOutletContext = { reload: accounts.reload };

  return (
    <>
      <PageHeader
        title={t('Contas')}
        description={t('Empresas, ONGs, escolas e universidades atendidas por esta plataforma.')}
        actions={<LinkButton to="new">{t('Nova conta')}</LinkButton>}
      />
      <Card>
        {accounts.loading && !accounts.data ? (
          <ListSkeleton rows={3} label={t('Carregando')} />
        ) : accounts.error ? (
          <EmptyState
            title={t('Não foi possível carregar.')}
            description={localizeApiError(accounts.error, t)}
            action={
              <Button variant="secondary" size="sm" onClick={() => void accounts.reload()}>
                {t('Tentar novamente')}
              </Button>
            }
          />
        ) : !accounts.data || accounts.data.length === 0 ? (
          <EmptyState
            title={t('Nenhuma conta ainda')}
            description={t('Crie a primeira conta para começar.')}
            action={<LinkButton to="new" size="sm">{t('Nova conta')}</LinkButton>}
          />
        ) : (
          accounts.data.map(account => (
            <ListRow
              key={account.id}
              title={account.name}
              meta={account.slug}
              actions={
                <>
                  {session?.activeAccount?.id !== account.id ? (
                    <Button size="sm" variant="ghost" onClick={() => void switchAccount(account.id)}>
                      {t('Usar esta conta')}
                    </Button>
                  ) : null}
                  <LinkButton to={`${account.id}/edit`} variant="ghost" size="sm">
                    {t('Editar')}
                  </LinkButton>
                  <Button size="sm" variant="danger" onClick={() => setPendingDelete(account)}>
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
        title={t('Excluir conta')}
        name={pendingDelete?.name ?? ''}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setPendingDelete(null)}
      />
    </>
  );
}
