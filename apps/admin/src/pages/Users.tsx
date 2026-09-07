import { useState } from 'react';
import { Button, Input, Card, Message } from '@argus/design-system';
import { call, Account } from '../api';

interface UsersProps {
  users: Account[];
  companyId: string | null;
  onReload: () => void;
}

export function Users({ users, companyId, onReload }: UsersProps) {
  const [userEmail, setUserEmail] = useState('manager@argus.local');
  const [userPassword, setUserPassword] = useState('Password123!');
  const [userRole, setUserRole] = useState('manager');
  const [message, setMessage] = useState('');

  async function createUser() {
    if (!companyId) {
      setMessage('Select a tenant before creating a user.');
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
      setMessage('User created.');
    } catch (error) {
      setMessage(String(error));
    }
  }

  async function deleteUser(user: Account) {
    if (!window.confirm(`Delete ${user.email}?`)) return;
    try {
      await call(`/v1/admin/users/${user.id}`, { method: 'DELETE' });
      onReload();
    } catch (error) {
      setMessage(String(error));
    }
  }

  return (
    <Card>
      <h2>Users</h2>
      {users.map(user => (
        <article key={user.id} className="argus-list-item">
          <b>{user.email}</b>
          <span>{user.role}</span>
          <Button size="sm" variant="danger" onClick={() => deleteUser(user)}>Delete</Button>
        </article>
      ))}
      <div className="argus-inline-form">
        <Input
          label="User email"
          value={userEmail}
          onChange={e => setUserEmail(e.target.value)}
        />
        <Input
          label="Password"
          type="password"
          value={userPassword}
          onChange={e => setUserPassword(e.target.value)}
        />
        <select
          aria-label="User role"
          value={userRole}
          onChange={e => setUserRole(e.target.value)}
        >
          <option value="manager">Manager</option>
          <option value="operator">Operator</option>
        </select>
        <Button onClick={createUser}>Create user</Button>
      </div>
      <Message text={message} />
    </Card>
  );
}
