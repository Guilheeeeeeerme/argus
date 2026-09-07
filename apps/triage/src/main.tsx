import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ThemeProvider, LocaleToggle } from '@argus/design-system';
import { I18nProvider, useT, useLocale } from '@argus/i18n';
import '@argus/design-system/tokens.css';
import '@argus/design-system/global.css';
import './style.css';
import { consumeTokenFromUrl, getToken, redirectToLogin } from './api';
import { loadSession, Session } from './api';
import { TriageWorkspace } from './pages/TriageWorkspace';

function TriageRoot() {
  const t = useT();
  const { locale, setLocale } = useLocale();
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
      <main>
        <LocaleToggle locale={locale} label={t('PT-BR')} ariaLabel={t('Switch language')} onLocaleChange={setLocale} />
        <p>{t('Checking session…')}</p>
      </main>
    );
  }
  if (companyless) {
    return (
      <main>
        <LocaleToggle locale={locale} label={t('PT-BR')} ariaLabel={t('Switch language')} onLocaleChange={setLocale} />
        <p>{t('No company assigned yet.')}</p>
        <p>{t('Ask an administrator for access.')}</p>
      </main>
    );
  }
  return session ? (
    <TriageWorkspace session={session} />
  ) : (
    <main><p>{t('Redirecting to sign in…')}</p></main>
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
