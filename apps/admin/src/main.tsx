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
  EmptyState,
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
      setCompanies((await call('/v1/auth/companies')) as Company[]);
      if (isPlatform(next.user.role)) {
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
      if (target !== APP && next.activeCompany) window.location.assign(withToken(target));
      else setMessage(t('Empresa atualizada.'));
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
          ? t('Estabelecimento ativo: {name}', {
              name: next.activeEstablishment?.name ?? '',
            })
          : t('Estabelecimento removido.'),
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
      brandMark={<img src="/brand.svg" alt="" width={24} height={24} />}
      meta={t('Administração')}
      actions={
        <>
          <ThemeToggle toDarkLabel={t('Mudar para modo escuro')} toLightLabel={t('Mudar para modo claro')} />
          <UserMenu
            name={displayName}
            email={session.user.email}
            locale={locale}
            locales={SUPPORTED_LOCALES.map(code => ({
              value: code,
              label: LOCALE_LABELS[code],
            }))}
            languageLabel={t('Idioma')}
            logoutLabel={t('Sair')}
            onLocaleChange={next => setLocale(next as typeof locale)}
            onLogout={() => setConfirmSignOut(true)}
          />
        </>
      }
      sidebar={
        <Sidenav
          brand="ARGUS"
          brandMark={<img src="/brand.svg" alt="" width={24} height={24} />}
          subtitle={t('Administração')}
          aria-label={t('Contexto de empresa')}
        >
          <div className="argus-sidenav__section">
              <label className="argus-sidenav__section-label" htmlFor="company-switcher">
                {t('Empresa')}
              </label>
              <select
                id="company-switcher"
                className="argus-select"
                aria-label={t('Empresa ativa')}
                value={session.activeCompany?.id ?? ''}
                onChange={e => void switchCompany(e.target.value)}
              >
                <option value="">{t('Nenhuma empresa selecionada')}</option>
                {companies.map(company => (
                  <option key={company.id} value={company.id}>
                    {company.name}
                  </option>
                ))}
              </select>
          </div>
          {session.activeCompany && (
            <div className="argus-sidenav__section">
              <label className="argus-sidenav__section-label" htmlFor="establishment-switcher">
                {t('Estabelecimento')}
              </label>
              <select
                id="establishment-switcher"
                className="argus-select"
                aria-label={t('Estabelecimento ativo')}
                value={session.activeEstablishment?.id ?? ''}
                onChange={e => void switchEstablishment(e.target.value)}
              >
                <option value="">{t('Nenhum estabelecimento selecionado')}</option>
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
              {t('Abrir Triagem')}
            </Button>
          </div>
        </Sidenav>
      }
    >
      {message ? <Message text={message} /> : null}

      <div className="argus-admin-sections">
        {!session.activeCompany && (
          <EmptyState
            title={t(companies.length ? 'Selecione uma empresa' : 'Nenhuma empresa atribuída ainda.')}
            description={t(companies.length ? 'Escolha uma empresa na barra lateral para continuar.' : 'Fale com um administrador para ter acesso.')}
          />
        )}
        {isPlatform(session.user.role) && (
          <>
            <Companies companies={companies} onReload={() => void load()} />
            <Users
              users={users}
              companies={companies}
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
        title={t('Sair?')}
        description={t('Encerrar a sessão neste dispositivo?')}
        confirmLabel={t('Sair')}
        cancelLabel={t('Cancelar')}
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
        <Skeleton width={180} height={20} aria-label={t('Carregando')} />
        <Skeleton width={120} height={14} />
      </div>
    );
  }
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
