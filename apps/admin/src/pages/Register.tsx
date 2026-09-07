import { FormEvent, useState } from 'react';
import { Button, Input, Card, Header, Message, LocaleToggle } from '@argus/design-system';
import { useT, useLocale, localizeApiError } from '@argus/i18n';
import { setToken, Session } from '@shared/auth';
import { call, returnTo, APP } from '../api';

export function Register({ onRegister }: { onRegister: (session: Session) => void }) {
  const t = useT();
  const { locale, setLocale } = useLocale();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (password.length < 8) {
      setMessage(t('Password must be at least 8 characters.'));
      return;
    }
    try {
      const session = (await call('/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })) as Session;
      if (session.token) setToken(session.token);
      setMessage('');
      onRegister(session);
      const target = returnTo();
      if (target !== APP) {
        window.location.assign(
          `${target}#token=${encodeURIComponent(session.token ?? '')}`,
        );
      } else {
        window.location.assign(APP);
      }
    } catch (error) {
      setMessage(localizeApiError(String(error), t));
    }
  }

  return (
    <main className="argus-login">
      <Card>
        <Header
          title="ARGUS"
          subtitle={t('Create your account.')}
          actions={<LocaleToggle locale={locale} label={t('PT-BR')} ariaLabel={t('Switch language')} onLocaleChange={setLocale} />}
        />
        <form onSubmit={submit}>
          <Input
            label={t('Email')}
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
          />
          <Input
            label={t('Password')}
            type="password"
            minLength={8}
            value={password}
            onChange={e => setPassword(e.target.value)}
          />
          <p className="argus-auth-hint">{t('At least 8 characters.')}</p>
          <Button type="submit">{t('Create account')}</Button>
        </form>
        <p className="argus-auth-link">
          {t('Already have an account?')} <a href="/">{t('Sign in')}</a>
        </p>
        <Message text={message} variant="error" />
      </Card>
    </main>
  );
}
