import { useState } from 'react';
import { Outlet } from 'react-router';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ListRow,
  ListSkeleton,
  PageHeader,
  useToast,
} from '@argus/design-system';
import { useT, localizeApiError, roleLabel } from '@argus/i18n';
import { useAsync, useMutation } from '@shared/hooks';
import { accounts as accountsApi, users as usersApi } from '../api/client';
import type { AdminUser } from '../api/types';
import { RequirePlatform } from '../app/guards';
import { useSession } from '../app/SessionProvider';
import { LinkButton } from '../components/LinkButton';
import { ConfirmDelete } from '../components/forms/ConfirmDelete';
import type { UsersOutletContext } from '../components/forms/UserForm';

export function UsersPage() {
  return (
    <RequirePlatform>
      <UsersList />
    </RequirePlatform>
  );
}

function UsersList() {
  const t = useT();
  const toast = useToast();
  const { session } = useSession();
  const users = useAsync(() => usersApi.list(), []);
  const accounts = useAsync(() => accountsApi.list(), []);
  const remove = useMutation((id: string) => usersApi.remove(id));
  const [pendingDelete, setPendingDelete] = useState<AdminUser | null>(null);

  async function confirmDelete() {
    if (!pendingDelete) return;
    const result = await remove.run(pendingDelete.id);
    if (!result.ok) {
      toast.error(localizeApiError(result.error, t));
      return;
    }
    toast.success(t('Usuário excluído.'));
    setPendingDelete(null);
    void users.reload();
  }

  const accountName = (id: string) => accounts.data?.find(c => c.id === id)?.name ?? id.slice(0, 8);
  const outletContext: UsersOutletContext = { accounts: accounts.data ?? [], reload: users.reload };

  return (
    <>
      <PageHeader
        title={t('Usuários')}
        description={t('Gestores e operadores das contas, além dos administradores da plataforma.')}
        actions={<LinkButton to="new">{t('Novo usuário')}</LinkButton>}
      />
      <Card>
        {users.loading && !users.data ? (
          <ListSkeleton rows={4} label={t('Carregando')} />
        ) : users.error ? (
          <EmptyState
            title={t('Não foi possível carregar.')}
            description={localizeApiError(users.error, t)}
            action={
              <Button variant="secondary" size="sm" onClick={() => void users.reload()}>
                {t('Tentar novamente')}
              </Button>
            }
          />
        ) : !users.data || users.data.length === 0 ? (
          <EmptyState
            title={t('Nenhum usuário ainda')}
            description={t('Crie um gestor ou operador e dê acesso às contas.')}
            action={<LinkButton to="new" size="sm">{t('Novo usuário')}</LinkButton>}
          />
        ) : (
          users.data.map(user => (
            <ListRow
              key={user.id}
              title={user.email}
              meta={
                user.account_ids.length
                  ? user.account_ids.map(accountName).join(' · ')
                  : t('Nenhum acesso')
              }
              actions={
                <>
                  <Badge variant={user.role === 'root' || user.role === 'admin' ? 'warning' : 'neutral'}>
                    {roleLabel(user.role, t)}
                  </Badge>
                  <LinkButton to={`${user.id}/edit`} variant="ghost" size="sm">
                    {t('Editar')}
                  </LinkButton>
                  <Button
                    size="sm"
                    variant="danger"
                    disabled={user.id === session?.user.id}
                    onClick={() => setPendingDelete(user)}
                  >
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
        title={t('Excluir usuário')}
        name={pendingDelete?.email ?? ''}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setPendingDelete(null)}
      />
    </>
  );
}
