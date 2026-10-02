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
      if (target !== APP && session.activeCompany) {
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
            label={t('English')}
            ariaLabel={t('Mudar idioma')}
            onLocaleChange={setLocale}
          />
          <ThemeToggle toDarkLabel={t('Mudar para modo escuro')} toLightLabel={t('Mudar para modo claro')} />
        </div>
        <Card>
          <h1 className="argus-auth__brand">
            <img src="/brand.svg" alt="" width={28} height={28} style={{ verticalAlign: 'middle', marginRight: '0.5rem' }} />
            ARGUS
          </h1>
          <p className="argus-auth__subtitle">{t('Entre para continuar.')}</p>
          <form onSubmit={submit}>
            <Input
              label={t('E-mail')}
              type="email"
              autoComplete="username"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
            />
            <Input
              label={t('Senha')}
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
            <Button type="submit" disabled={submitting}>
              {t('Entrar')}
            </Button>
          </form>
          <Message text={message} variant="error" />
        </Card>
      </div>
    </main>
  );
}
