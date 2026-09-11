import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  ThemeProvider,
  ThemeToggle,
  AppShell,
  Sidenav,
  Button,
  Message,
  Skeleton,
  AlertDialog,
  UserMenu,
} from '@argus/design-system';
import { I18nProvider, useT, useLocale, SUPPORTED_LOCALES } from '@argus/i18n';
import '@argus/design-system/tokens.css';
import '@argus/design-system/global.css';
import './style.css';
import {
  clearToken,
  consumeTokenFromUrl,
  getToken,
  getSession,
  isAllowedReturn,
  TRIAGE_ORIGIN,
  Session as AuthSession,
} from '@shared/auth';
import { call, returnTo, APP, switchContext, Session, Company, Establishment, Account } from './api';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Companies } from './pages/Companies';
import { Users } from './pages/Users';
import { Establishments } from './pages/Establishments';
import { Webhooks } from './pages/Webhooks';

function isPlatform(role: string): boolean {
  return role === 'root' || role === 'admin';
}

const LOCALE_LABELS: Record<(typeof SUPPORTED_LOCALES)[number], string> = {
  en: 'English',
  'pt-BR': 'Português (Brasil)',
};

function App({ initial }: { initial: Session }) {
  const t = useT();
  const { locale, setLocale } = useLocale();
  const [session, setSession] = useState(initial);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [establishments, setEstablishments] = useState<Establishment[]>([]);
  const [users, setUsers] = useState<Account[]>([]);
  const [message, setMessage] = useState('');
  const [confirmSignOut, setConfirmSignOut] = useState(false);

  async function load(next = session) {
    setSession(next);
    try {
      if (isPlatform(next.user.role)) {
        setCompanies((await call('/v1/admin/companies')) as Company[]);
        setUsers((await call('/v1/admin/users')) as Account[]);
      }
      if (next.activeCompany) {
        setEstablishments(
          (await call(
            `/v1/companies/${next.activeCompany.id}/establishments`,
          )) as Establishment[],
        );
      } else {
        setEstablishments([]);
      }
    } catch (error) {
      setMessage(String(error));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function switchCompany(id: string) {
    try {
      const next = await switchContext({ companyId: id || null });
      await load(next);
      const target = returnTo();
      if (target !== APP) window.location.assign(withToken(target));
      else setMessage(t('Company context updated.'));
    } catch (error) {
      setMessage(String(error));
    }
  }

  async function switchEstablishment(id: string) {
    try {
      const next = await switchContext({ establishmentId: id || null });
      await load(next);
      setMessage(
        id
          ? t('Active establishment: {name}', {
              name: next.activeEstablishment?.name ?? '',
            })
          : t('Establishment cleared.'),
      );
    } catch (error) {
      setMessage(String(error));
    }
  }

  function withToken(target: string): string {
    const token = getToken();
    if (!token) return target;
    return `${target}#token=${encodeURIComponent(token)}`;
  }

  function signOut() {
    void call('/v1/auth/logout', { method: 'POST' });
    clearToken();
    window.location.assign(APP);
  }

  const displayName = session.user.email.split('@')[0] || session.user.email;

  return (
    <AppShell
      brand="ARGUS"
      meta={t('Administration')}
      actions={
        <>
          <ThemeToggle />
          <UserMenu
            name={displayName}
            email={session.user.email}
            locale={locale}
            locales={SUPPORTED_LOCALES.map(code => ({
              value: code,
              label: LOCALE_LABELS[code],
            }))}
            languageLabel={t('Language')}
            logoutLabel={t('Log out')}
            onLocaleChange={next => setLocale(next as typeof locale)}
            onLogout={() => setConfirmSignOut(true)}
          />
        </>
      }
      sidebar={
        <Sidenav brand="ARGUS" subtitle={t('Administration')} aria-label={t('Tenant context')}>
          {isPlatform(session.user.role) && (
            <div className="argus-sidenav__section">
              <label className="argus-sidenav__section-label" htmlFor="company-switcher">
                {t('Company')}
              </label>
              <select
                id="company-switcher"
                className="argus-select"
                aria-label={t('Active company')}
                value={session.activeCompany?.id ?? ''}
                onChange={e => void switchCompany(e.target.value)}
              >
                <option value="">{t('All companies')}</option>
                {companies.map(company => (
                  <option key={company.id} value={company.id}>
                    {company.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          {!isPlatform(session.user.role) && (
            <div className="argus-sidenav__section">
              <span className="argus-sidenav__section-label">{t('Company')}</span>
              <span className="argus-list-row__title">
                {session.activeCompany?.name ?? t('All companies')}
              </span>
            </div>
          )}
          {session.activeCompany && (
            <div className="argus-sidenav__section">
              <label className="argus-sidenav__section-label" htmlFor="establishment-switcher">
                {t('Establishment')}
              </label>
              <select
                id="establishment-switcher"
                className="argus-select"
                aria-label={t('Active establishment')}
                value={session.activeEstablishment?.id ?? ''}
                onChange={e => void switchEstablishment(e.target.value)}
              >
                <option value="">{t('No establishment selected')}</option>
                {establishments.map(establishment => (
                  <option key={establishment.id} value={establishment.id}>
                    {establishment.name}
                  </option>
                ))}
              </select>
            </div>
          )}
          <div className="argus-sidenav__footer">
            <Button
              variant="secondary"
              onClick={() =>
                window.location.assign(
                  `${TRIAGE_ORIGIN}?returnTo=${encodeURIComponent(withToken(window.location.href))}`,
                )
              }
            >
              {t('Open Triage')}
            </Button>
          </div>
        </Sidenav>
      }
    >
      {message ? <Message text={message} /> : null}

      <div className="argus-admin-sections">
        {isPlatform(session.user.role) && (
          <>
            <Companies companies={companies} onReload={() => void load()} />
            <Users
              users={users}
              companyId={session.activeCompany?.id ?? null}
              onReload={() => void load()}
            />
          </>
        )}
        {session.activeCompany && (
          <>
            <Establishments
              establishments={establishments}
              companyId={session.activeCompany.id}
              onReload={() => void load()}
            />
            <Webhooks
              establishments={establishments}
              companyId={session.activeCompany.id}
            />
          </>
        )}
      </div>

      <AlertDialog
        open={confirmSignOut}
        title={t('Log out?')}
        description={t('End your session on this device?')}
        confirmLabel={t('Log out')}
        cancelLabel={t('Cancel')}
        tone="primary"
        onConfirm={signOut}
        onCancel={() => setConfirmSignOut(false)}
      />
    </AppShell>
  );
}

function SsoHandoffPage() {
  const params = new URLSearchParams(window.location.search);
  const target = params.get('returnUrl') ?? APP;
  const token = getToken();

  useEffect(() => {
    if (token && isAllowedReturn(target)) {
      window.location.assign(`${target}#token=${encodeURIComponent(token)}`);
    }
  }, [token, target]);

  if (token && isAllowedReturn(target)) return null;
  return (
    <Login
      onLogin={(session: AuthSession) => {
        if (isAllowedReturn(target)) {
          window.location.assign(
            `${target}#token=${encodeURIComponent(session.token ?? getToken() ?? '')}`,
          );
        }
      }}
    />
  );
}

function LocaleAware() {
  const t = useT();
  const [session, setSession] = useState<Session | null>(null);
  const [booted, setBooted] = useState(false);

  useEffect(() => {
    consumeTokenFromUrl();
    if (window.location.pathname === '/register') {
      if (getToken()) {
        getSession()
          .then(() => {
            window.location.assign(APP);
          })
          .catch(() => {
            clearToken();
            setBooted(true);
          });
      } else {
        setBooted(true);
      }
      return;
    }
    if (window.location.pathname === '/sso/handoff') {
      setBooted(true);
      return;
    }
    if (getToken()) {
      getSession()
        .then(setSession)
        .catch(() => clearToken())
        .finally(() => setBooted(true));
    } else {
      setBooted(true);
    }
  }, []);

  if (!booted) {
    return (
      <div className="argus-boot" role="status" aria-live="polite">
        <Skeleton width={180} height={20} aria-label={t('Loading')} />
        <Skeleton width={120} height={14} />
      </div>
    );
  }
  if (window.location.pathname === '/register') return <Register onRegister={setSession} />;
  if (window.location.pathname === '/sso/handoff') return <SsoHandoffPage />;
  return session ? <App initial={session} /> : <Login onLogin={setSession} />;
}

function Root() {
  return (
    <ThemeProvider>
      <I18nProvider>
        <LocaleAware />
      </I18nProvider>
    </ThemeProvider>
  );
}

createRoot(document.getElementById('root')!).render(<Root />);
