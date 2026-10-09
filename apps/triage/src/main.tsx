import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  ThemeProvider,
  ToastProvider,
  LocaleToggle,
  ThemeToggle,
  Skeleton,
  EmptyState,
  Card,
  Button,
} from '@argus/design-system';
import { I18nProvider, useT, useLocale } from '@argus/i18n';
import '@argus/design-system/tokens.css';
import '@argus/design-system/global.css';
import './style.css';
import { consumeTokenFromUrl, getToken, redirectToLogin } from './api';
import { loadSession, Session, selectAccount } from './api';
import { TriageWorkspace } from './pages/TriageWorkspace';

function BootToolbar() {
  const t = useT();
  const { locale, setLocale } = useLocale();
  return (
    <div className="argus-boot__toolbar">
      <LocaleToggle
        locale={locale}
        label={t('English')}
        ariaLabel={t('Mudar idioma')}
        onLocaleChange={setLocale}
      />
      <ThemeToggle toDarkLabel={t('Mudar para modo escuro')} toLightLabel={t('Mudar para modo claro')} />
    </div>
  );
}

function TriageRoot() {
  const t = useT();
  const [session, setSession] = useState<Session | null>(null);
  const [accountless, setAccountless] = useState(false);
  const [bootError, setBootError] = useState(false);
  const [booted, setBooted] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      consumeTokenFromUrl();
      if (!getToken()) {
        redirectToLogin();
        return;
      }
      const next = await loadSession();
      if (cancelled) return;
      if (!next.ok) {
        // Keep operators on triage when a token exists but /me fails (proxy/CORS/local-vs-remote),
        // instead of bouncing into a prod SSO loop that cannot return to localhost.
        setBootError(true);
        setBooted(true);
        return;
      }
      if ('accountless' in next) setAccountless(true);
      else setSession(next.session);
      setBooted(true);
    }
    void boot();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!booted) {
    return (
      <main className="argus-boot">
        <BootToolbar />
        <Skeleton width={200} height={20} aria-label={t('Verificando sessão…')} />
        <Skeleton width={140} height={14} aria-label="" />
        <p>{t('Verificando sessão…')}</p>
      </main>
    );
  }
  if (bootError) {
    return (
      <main className="argus-boot argus-boot--blocked">
        <BootToolbar />
        <Card className="argus-auth__panel argus-triage-blocked">
          <EmptyState
            title={t('Não foi possível carregar.')}
            description={t('Sessão inválida ou API indisponível. Entre novamente ou selecione uma conta.')}
          />
          <div className="argus-triage-blocked__actions">
            <Button onClick={() => redirectToLogin()}>{t('Entrar')}</Button>
            <Button variant="secondary" onClick={selectAccount}>
              {t('Selecione uma conta')}
            </Button>
          </div>
        </Card>
      </main>
    );
  }
  if (accountless) {
    return (
      <main className="argus-boot argus-boot--blocked" aria-labelledby="argus-triage-accountless-title">
        <BootToolbar />
        <Card className="argus-auth__panel argus-triage-blocked">
          <EmptyState
            title={t('Nenhuma conta selecionada')}
            description={t(
              'A triagem exige uma conta ativa. Selecione uma conta na administração ou peça acesso a um administrador.',
            )}
          />
          <div className="argus-triage-blocked__actions">
            <Button onClick={selectAccount}>{t('Selecione uma conta')}</Button>
          </div>
          <p id="argus-triage-accountless-title" className="sr-only">
            {t('Nenhuma conta selecionada')}
          </p>
        </Card>
      </main>
    );
  }
  return session ? (
    <TriageWorkspace session={session} />
  ) : (
    <main className="argus-boot">
      <p>{t('Redirecionando para o login…')}</p>
    </main>
  );
}

function Providers() {
  const t = useT();
  return (
    <ToastProvider closeLabel={t('Fechar')}>
      <TriageRoot />
    </ToastProvider>
  );
}

function Root() {
  return (
    <ThemeProvider>
      <I18nProvider>
        <Providers />
      </I18nProvider>
    </ThemeProvider>
  );
}

createRoot(document.getElementById('root')!).render(<Root />);
