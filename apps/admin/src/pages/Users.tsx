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
import { useT, localizeApiError } from '@argus/i18n';
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
      setMessage(t('User created.'));
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
      setMessage(t('Company access updated.'));
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
      <h2>{t('Users')}</h2>
      {users.length === 0 ? (
        <EmptyState
          title={t('No users yet')}
          description={t('Create a manager or operator for the active company.')}
        />
      ) : (
        users.map(user => (
          <ListRow
            key={user.id}
            title={user.email}
            meta={user.role}
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
                    {t(user.company_ids.includes(company.id) ? 'Remove access to {name}' : 'Add access to {name}', { name: company.name })}
                  </Button>
                ))}
                <Button size="sm" variant="danger" onClick={() => setPendingDelete(user)}>
                  {t('Delete')}
                </Button>
              </>
            }
          />
        ))
      )}
      <div className="argus-inline-form">
        <Input
          label={t('User email')}
          value={userEmail}
          onChange={e => setUserEmail(e.target.value)}
        />
        <Input
          label={t('Password')}
          type="password"
          value={userPassword}
          onChange={e => setUserPassword(e.target.value)}
        />
        <Select
          label={t('User role')}
          value={userRole}
          onChange={e => setUserRole(e.target.value)}
          options={[
            { value: 'manager', label: t('Manager') },
            { value: 'operator', label: t('Operator') },
          ]}
        />
        <Button onClick={createUser}>{t('Create user')}</Button>
      </div>
      <Message text={message} />

      <AlertDialog
        open={Boolean(pendingDelete)}
        title={t('Delete user')}
        description={t('Delete {name}? This cannot be undone.', {
          name: pendingDelete?.email ?? '',
        })}
        confirmLabel={t('Delete')}
        cancelLabel={t('Cancel')}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setPendingDelete(null)}
      />
    </Card>
  );
}
