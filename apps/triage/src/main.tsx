import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  ThemeProvider,
  LocaleToggle,
  ThemeToggle,
  Skeleton,
  EmptyState,
  Card,
} from '@argus/design-system';
import { I18nProvider, useT, useLocale } from '@argus/i18n';
import '@argus/design-system/tokens.css';
import '@argus/design-system/global.css';
import './style.css';
import { consumeTokenFromUrl, getToken, redirectToLogin } from './api';
import { loadSession, Session } from './api';
import { TriageWorkspace } from './pages/TriageWorkspace';

function BootToolbar() {
  const t = useT();
  const { locale, setLocale } = useLocale();
  return (
    <div className="argus-boot__toolbar">
      <LocaleToggle
        locale={locale}
        label={t('PT-BR')}
        ariaLabel={t('Switch language')}
        onLocaleChange={setLocale}
      />
      <ThemeToggle />
    </div>
  );
}

function TriageRoot() {
  const t = useT();
  const [session, setSession] = useState<Session | null>(null);
  const [companyless, setCompanyless] = useState(false);
  const [booted, setBooted] = useState(false);

  useEffect(() => {
    consumeTokenFromUrl();
    if (!getToken()) {
      redirectToLogin();
      return;
    }
    loadSession().then(next => {
      if (!next.ok) redirectToLogin();
      else if ('companyless' in next) setCompanyless(true);
      else setSession(next.session);
      setBooted(true);
    });
  }, []);

  if (!booted) {
    return (
      <main className="argus-boot">
        <BootToolbar />
        <Skeleton width={200} height={20} aria-label={t('Checking session…')} />
        <Skeleton width={140} height={14} />
        <p>{t('Checking session…')}</p>
      </main>
    );
  }
  if (companyless) {
    return (
      <main className="argus-boot">
        <BootToolbar />
        <Card className="argus-auth__panel">
          <EmptyState
            title={t('No company assigned yet.')}
            description={t('Ask an administrator for access.')}
          />
        </Card>
      </main>
    );
  }
  return session ? (
    <TriageWorkspace session={session} />
  ) : (
    <main className="argus-boot">
      <p>{t('Redirecting to sign in…')}</p>
    </main>
  );
}

function Root() {
  return (
    <ThemeProvider>
      <I18nProvider>
        <TriageRoot />
      </I18nProvider>
    </ThemeProvider>
  );
}

createRoot(document.getElementById('root')!).render(<Root />);
