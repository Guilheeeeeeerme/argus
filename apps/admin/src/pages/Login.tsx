import { FormEvent, useState } from 'react';
import { Button, Input, Card, Header, Message } from '@argus/design-system';
import { setToken, Session } from '@shared/auth';
import { call, returnTo, APP } from '../api';

export function Login({ onLogin }: { onLogin: (session: Session) => void }) {
  const [email, setEmail] = useState('root@argus.local');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      const session = (await call('/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })) as Session;
      if (session.token) setToken(session.token);
      onLogin(session);
      const target = returnTo();
      if (target !== APP) {
        window.location.assign(
          `${target}#token=${encodeURIComponent(session.token ?? '')}`,
        );
      }
    } catch (error) {
      setMessage(String(error));
    }
  }

  return (
    <main className="argus-login">
      <Card>
        <Header title="ARGUS" subtitle="Sign in to continue." />
        <form onSubmit={submit}>
          <Input
            label="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
          />
          <Button type="submit">Sign in</Button>
        </form>
        <Message text={message} />
      </Card>
    </main>
  );
}
