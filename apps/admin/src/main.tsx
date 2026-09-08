import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  ThemeProvider,
  ThemeToggle,
  LocaleToggle,
  AppShell,
  Sidenav,
  Button,
  Message,
  Skeleton,
  AlertDialog,
} from '@argus/design-system';
import { I18nProvider, useT, useLocale } from '@argus/i18n';
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
import { call, returnTo, APP, switchContext, Session, Company, Location, Account } from './api';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Companies } from './pages/Companies';
import { Users } from './pages/Users';
import { Locations } from './pages/Locations';

function isPlatform(role: string): boolean {
  return role === 'root' || role === 'admin';
}

function App({ initial }: { initial: Session }) {
  const t = useT();
  const { locale, setLocale } = useLocale();
  const [session, setSession] = useState(initial);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
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
        setLocations(
          (await call(`/v1/companies/${next.activeCompany.id}/locations`)) as Location[],
        );
      } else {
        setLocations([]);
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

  async function switchLocation(id: string) {
    try {
      const next = await switchContext({ locationId: id || null });
      await load(next);
      setMessage(
        id
          ? t('Active location: {name}', { name: next.activeLocation?.name ?? '' })
          : t('Location cleared.'),
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

  return (
    <AppShell
      brand="ARGUS"
      meta={t('Administration')}
      actions={
        <>
          <LocaleToggle
            locale={locale}
            label={t('PT-BR')}
            ariaLabel={t('Switch language')}
            onLocaleChange={setLocale}
          />
          <ThemeToggle />
        </>
      }
    >
      <Sidenav aria-label={t('Tenant context')}>
        {isPlatform(session.user.role) && (
          <label>
            {t('Company')}
            <select
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
          </label>
        )}
        {session.activeCompany && (
          <label>
            {t('Location')}
            <select
              aria-label={t('Active location')}
              value={session.activeLocation?.id ?? ''}
              onChange={e => void switchLocation(e.target.value)}
            >
              <option value="">{t('No location selected')}</option>
              {locations.map(location => (
                <option key={location.id} value={location.id}>
                  {location.name}
                </option>
              ))}
            </select>
          </label>
        )}
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
        <Button variant="ghost" onClick={() => setConfirmSignOut(true)}>
          {t('Sign out')}
        </Button>
      </Sidenav>

      <Message
        text={
          message ||
          t('Signed in as {email} ({role})', {
            email: session.user.email,
            role: session.user.role,
          })
        }
      />

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
          <Locations
            locations={locations}
            companyId={session.activeCompany.id}
            onReload={() => void load()}
          />
        )}
      </div>

      <AlertDialog
        open={confirmSignOut}
        title={t('Sign out')}
        description={t('End your session on this device?')}
        confirmLabel={t('Sign out')}
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
