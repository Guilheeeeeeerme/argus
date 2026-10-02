import { useState } from 'react';
import {
  Button,
  Input,
  Select,
  Card,
  Message,
  ListRow,
  EmptyState,
  AlertDialog,
} from '@argus/design-system';
import { useT, localizeApiError, roleLabel } from '@argus/i18n';
import { call, Account, Company } from '../api';

interface UsersProps {
  users: Account[];
  companies: Company[];
  companyId: string | null;
  onReload: () => void;
}

export function Users({ users, companies, companyId, onReload }: UsersProps) {
  const t = useT();
  const [userEmail, setUserEmail] = useState('manager@argus.local');
  const [userPassword, setUserPassword] = useState('Password123!');
  const [userRole, setUserRole] = useState('manager');
  const [message, setMessage] = useState('');
  const [pendingDelete, setPendingDelete] = useState<Account | null>(null);

  async function createUser() {
    try {
      await call('/v1/admin/users', {
        method: 'POST',
        body: JSON.stringify({
          company_ids: companyId ? [companyId] : [],
          email: userEmail,
          password: userPassword,
          role: userRole,
        }),
      });
      onReload();
      setMessage(t('Usuário criado.'));
    } catch (error) {
      setMessage(localizeApiError(String(error), t));
    }
  }

  async function updateMembership(user: Account, id: string, assigned: boolean) {
    const ids = assigned ? [...user.company_ids, id] : user.company_ids.filter(value => value !== id);
    try {
      await call(`/v1/admin/users/${user.id}`, {
        method: 'PATCH', body: JSON.stringify({ company_ids: ids }),
      });
      onReload();
      setMessage(t('Acesso à empresa atualizado.'));
    } catch (error) {
      setMessage(localizeApiError(String(error), t));
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    const user = pendingDelete;
    setPendingDelete(null);
    try {
      await call(`/v1/admin/users/${user.id}`, { method: 'DELETE' });
      onReload();
    } catch (error) {
      setMessage(localizeApiError(String(error), t));
    }
  }

  return (
    <Card>
      <h2>{t('Usuários')}</h2>
      {users.length === 0 ? (
        <EmptyState
          title={t('Nenhum usuário ainda')}
          description={t('Crie um gestor ou operador para esta empresa.')}
        />
      ) : (
        users.map(user => (
          <ListRow
            key={user.id}
            title={user.email}
            meta={roleLabel(user.role, t)}
            actions={
              <>
                {companies.map(company => (
                  <Button
                    key={company.id}
                    size="sm"
                    variant="secondary"
                    aria-pressed={user.company_ids.includes(company.id)}
                    onClick={() => void updateMembership(user, company.id, !user.company_ids.includes(company.id))}
                  >
                    {t(user.company_ids.includes(company.id) ? 'Remover acesso a {name}' : 'Dar acesso a {name}', { name: company.name })}
                  </Button>
                ))}
                <Button size="sm" variant="danger" onClick={() => setPendingDelete(user)}>
                  {t('Excluir')}
                </Button>
              </>
            }
          />
        ))
      )}
      <div className="argus-inline-form">
        <Input
          label={t('E-mail do usuário')}
          value={userEmail}
          onChange={e => setUserEmail(e.target.value)}
        />
        <Input
          label={t('Senha')}
          type="password"
          value={userPassword}
          onChange={e => setUserPassword(e.target.value)}
        />
        <Select
          label={t('Função do usuário')}
          value={userRole}
          onChange={e => setUserRole(e.target.value)}
          options={[
            { value: 'manager', label: t('Gestor') },
            { value: 'operator', label: t('Operador') },
          ]}
        />
        <Button onClick={createUser}>{t('Criar usuário')}</Button>
      </div>
      <Message text={message} />

      <AlertDialog
        open={Boolean(pendingDelete)}
        title={t('Excluir usuário')}
        description={t('Excluir {name}? Essa ação não pode ser desfeita.', {
          name: pendingDelete?.email ?? '',
        })}
        confirmLabel={t('Excluir')}
        cancelLabel={t('Cancelar')}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setPendingDelete(null)}
      />
    </Card>
  );
}
