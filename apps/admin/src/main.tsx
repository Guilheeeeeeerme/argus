import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ThemeProvider, ThemeToggle, Header, Sidenav, Button, Message } from '@argus/design-system';
import '@argus/design-system/tokens.css';
import '@argus/design-system/global.css';
import './style.css';
import {
  clearToken,
  consumeTokenFromUrl,
  getToken,
  getSession,
  isAllowedReturn,
  setToken,
  TRIAGE_ORIGIN,
  Session as AuthSession,
} from '@shared/auth';
import { call, returnTo, APP, switchContext, Session, Company, Location, Account } from './api';
import { Login } from './pages/Login';
import { Companies } from './pages/Companies';
import { Users } from './pages/Users';
import { Locations } from './pages/Locations';

function isPlatform(role: string): boolean {
  return role === 'root' || role === 'admin';
}

function App({ initial }: { initial: Session }) {
  const [session, setSession] = useState(initial);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [users, setUsers] = useState<Account[]>([]);
  const [message, setMessage] = useState('');

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
      }
    } catch (error) {
      setMessage(String(error));
    }
  }

  useEffect(() => { void load(); }, []);

  async function switchCompany(id: string) {
    try {
      const next = await switchContext({ companyId: id || null });
      await load(next);
      const target = returnTo();
      if (target !== APP) window.location.assign(withToken(target));
      else setMessage('Company context updated.');
    } catch (error) {
      setMessage(String(error));
    }
  }

  async function switchLocation(id: string) {
    try {
      const next = await switchContext({ locationId: id || null });
      await load(next);
      setMessage(id ? `Active location: ${next.activeLocation?.name}` : 'Location cleared.');
    } catch (error) {
      setMessage(String(error));
    }
  }

  async function deleteCompany(company: Company) {
    if (!window.confirm(`Delete ${company.name}?`)) return;
    try {
      await call(`/v1/admin/companies/${company.id}`, { method: 'DELETE' });
      await switchContext({ companyId: null });
      await load(await getSession());
    } catch (error) {
      setMessage(String(error));
    }
  }

  function withToken(target: string): string {
    const token = getToken();
    if (!token) return target;
    return `${target}#token=${encodeURIComponent(token)}`;
  }

  return (
    <main className="argus-admin">
      <Header
        title="ARGUS"
        subtitle="Administration"
        actions={<ThemeToggle />}
      />
      <Sidenav>
        {isPlatform(session.user.role) && (
          <label>
            Company
            <select
              aria-label="Active company"
              value={session.activeCompany?.id ?? ''}
              onChange={e => void switchCompany(e.target.value)}
            >
              <option value="">All companies</option>
              {companies.map(company => (
                <option key={company.id} value={company.id}>{company.name}</option>
              ))}
            </select>
          </label>
        )}
        {session.activeCompany && (
          <label>
            Location
            <select
              aria-label="Active location"
              value={session.activeLocation?.id ?? ''}
              onChange={e => void switchLocation(e.target.value)}
            >
              <option value="">No location selected</option>
              {locations.map(location => (
                <option key={location.id} value={location.id}>{location.name}</option>
              ))}
            </select>
          </label>
        )}
        <Button
          variant="ghost"
          onClick={() => window.location.assign(`${TRIAGE_ORIGIN}?returnTo=${encodeURIComponent(withToken(window.location.href))}`)}
        >
          Open Triage
        </Button>
        <Button
          variant="ghost"
          onClick={() => { void call('/v1/auth/logout', { method: 'POST' }); clearToken(); window.location.assign(APP); }}
        >
          Sign out
        </Button>
      </Sidenav>
      <Message text={message || `Signed in as ${session.user.email} (${session.user.role})`} />
      {isPlatform(session.user.role) && (
        <>
          <Companies companies={companies} onReload={() => void load()} />
          <Users users={users} companyId={session.activeCompany?.id ?? null} onReload={() => void load()} />
        </>
      )}
      {session.activeCompany && (
        <Locations
          locations={locations}
          companyId={session.activeCompany.id}
          onReload={() => void load()}
        />
      )}
    </main>
  );
}

function SsoHandoff() {
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
          window.location.assign(`${target}#token=${encodeURIComponent(session.token ?? getToken() ?? '')}`);
        }
      }}
    />
  );
}

function Root() {
  const [session, setSession] = useState<Session | null>(null);
  const [booted, setBooted] = useState(false);

  useEffect(() => {
    consumeTokenFromUrl();
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

  if (!booted) return null;
  if (window.location.pathname === '/sso/handoff') return <SsoHandoff />;
  return session ? <App initial={session} /> : <Login onLogin={setSession} />;
}

createRoot(document.getElementById('root')!).render(
  <ThemeProvider>
    <Root />
  </ThemeProvider>
);
