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
  const [booted, setBooted] = useState(false);

  useEffect(() => {
    consumeTokenFromUrl();
    if (!getToken()) {
      redirectToLogin();
      return;
    }
    loadSession().then(next => {
      if (!next.ok) redirectToLogin();
      else if ('accountless' in next) setAccountless(true);
      else setSession(next.session);
      setBooted(true);
    });
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
  if (accountless) {
    return (
      <main className="argus-boot">
        <BootToolbar />
        <Card className="argus-auth__panel">
          <EmptyState
            title={t('Nenhuma conta selecionada')}
            description={t('Selecione uma conta ou peça acesso a um administrador.')}
          />
          <Button onClick={selectAccount}>{t('Selecione uma conta')}</Button>
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
