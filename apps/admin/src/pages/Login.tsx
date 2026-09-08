import { FormEvent, useState } from 'react';
import {
  Button,
  Input,
  Card,
  Message,
  LocaleToggle,
  ThemeToggle,
} from '@argus/design-system';
import { useT, useLocale, localizeApiError } from '@argus/i18n';
import { setToken, Session } from '@shared/auth';
import { call, returnTo, APP } from '../api';

export function Login({ onLogin }: { onLogin: (session: Session) => void }) {
  const t = useT();
  const { locale, setLocale } = useLocale();
  const [email, setEmail] = useState('root@argus.local');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
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
      setMessage(localizeApiError(String(error), t));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="argus-auth">
      <div className="argus-auth__panel">
        <div className="argus-auth__toolbar">
          <LocaleToggle
            locale={locale}
            label={t('PT-BR')}
            ariaLabel={t('Switch language')}
            onLocaleChange={setLocale}
          />
          <ThemeToggle />
        </div>
        <Card>
          <h1 className="argus-auth__brand">ARGUS</h1>
          <p className="argus-auth__subtitle">{t('Sign in to continue.')}</p>
          <form onSubmit={submit}>
            <Input
              label={t('Email')}
              type="email"
              autoComplete="username"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
            />
            <Input
              label={t('Password')}
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
            <Button type="submit" disabled={submitting}>
              {t('Sign in')}
            </Button>
          </form>
          <p className="argus-auth__link">
            {t('No account?')} <a href="/register">{t('Register')}</a>
          </p>
          <Message text={message} variant="error" />
        </Card>
      </div>
    </main>
  );
}
