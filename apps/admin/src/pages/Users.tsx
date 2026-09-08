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
import { call, Account } from '../api';

interface UsersProps {
  users: Account[];
  companyId: string | null;
  onReload: () => void;
}

export function Users({ users, companyId, onReload }: UsersProps) {
  const t = useT();
  const [userEmail, setUserEmail] = useState('manager@argus.local');
  const [userPassword, setUserPassword] = useState('Password123!');
  const [userRole, setUserRole] = useState('manager');
  const [message, setMessage] = useState('');
  const [pendingDelete, setPendingDelete] = useState<Account | null>(null);

  async function createUser() {
    if (!companyId) {
      setMessage(t('Select a tenant before creating a user.'));
      return;
    }
    try {
      await call('/v1/admin/users', {
        method: 'POST',
        body: JSON.stringify({
          company_id: companyId,
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
              <Button size="sm" variant="danger" onClick={() => setPendingDelete(user)}>
                {t('Delete')}
              </Button>
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
