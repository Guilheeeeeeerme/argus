import { useState } from 'react';
import {
  Button,
  Card,
  Form,
  FormError,
  Input,
  LocaleToggle,
  ThemeToggle,
} from '@argus/design-system';
import { useT, useLocale, localizeApiError } from '@argus/i18n';
import { useMutation } from '@shared/hooks';
import { setToken, type Session } from '@shared/auth';
import { auth, returnTo, APP } from '../api/client';
import { useSession } from '../app/SessionProvider';

interface LoginPageProps {
  /** Override the default behaviour (store session, honour `?returnTo=`). Used by the SSO handoff. */
  onLogin?: (session: Session) => void;
}

export function LoginPage({ onLogin }: LoginPageProps) {
  const t = useT();
  const { locale, setLocale } = useLocale();
  const { setSession } = useSession();
  const [email, setEmail] = useState(import.meta.env.DEV ? 'root@argus.local' : '');
  const [password, setPassword] = useState('');
  const login = useMutation(auth.login);
  const [fieldError, setFieldError] = useState<{ email?: string; password?: string }>({});

  async function submit() {
    const errors: { email?: string; password?: string } = {};
    if (!email.trim()) errors.email = t('Campo obrigatório');
    if (!password) errors.password = t('Campo obrigatório');
    setFieldError(errors);
    if (errors.email || errors.password) return;
    const result = await login.run(email.trim(), password);
    if (!result.ok) return;
    const session = result.data;
    if (session.token) setToken(session.token);
    if (onLogin) {
      onLogin(session);
      return;
    }
    setSession(session);
    const target = returnTo();
    if (target !== APP && session.activeAccount) {
      window.location.assign(`${target}#token=${encodeURIComponent(session.token ?? '')}`);
    }
  }

  return (
    <main className="argus-auth">
      <div className="argus-auth__panel">
        <div className="argus-auth__toolbar">
          <LocaleToggle
            locale={locale}
            label={locale === 'en' ? 'EN' : 'PT-BR'}
            ariaLabel={t('Mudar idioma')}
            onLocaleChange={setLocale}
          />
          <ThemeToggle toDarkLabel={t('Mudar para modo escuro')} toLightLabel={t('Mudar para modo claro')} />
        </div>
        <Card>
          <h1 className="argus-auth__brand">
            <img src="/brand.svg" alt="" width={28} height={28} className="argus-auth__brand-mark" />
            ARGUS
          </h1>
          <p className="argus-auth__subtitle">{t('Entre para continuar.')}</p>
          <Form onSubmit={() => void submit()} busy={login.pending}>
            <FormError message={login.error ? localizeApiError(login.error, t) : null} />
            <Input
              label={t('E-mail')}
              type="email"
              autoComplete="username"
              value={email}
              error={fieldError.email}
              onChange={e => setEmail(e.target.value)}
              required
            />
            <Input
              label={t('Senha')}
              type="password"
              autoComplete="current-password"
              value={password}
              error={fieldError.password}
              onChange={e => setPassword(e.target.value)}
              required
            />
            <Button type="submit" loading={login.pending}>
              {t('Entrar')}
            </Button>
          </Form>
        </Card>
      </div>
    </main>
  );
}
