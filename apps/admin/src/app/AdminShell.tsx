import { useState } from 'react';
import { NavLink, Outlet } from 'react-router';
import {
  AlertDialog,
  AppShell,
  Button,
  Select,
  Sidenav,
  Spinner,
  ThemeToggle,
  UserMenu,
} from '@argus/design-system';
import { useT, useLocale, SUPPORTED_LOCALES } from '@argus/i18n';
import { TRIAGE_ORIGIN } from '@shared/auth';
import { withToken } from '../api/client';
import { useSession } from './SessionProvider';

const LOCALE_LABELS: Record<(typeof SUPPORTED_LOCALES)[number], string> = {
  en: 'English',
  'pt-BR': 'Português (Brasil)',
};

function navClass({ isActive }: { isActive: boolean }): string {
  return ['argus-shell-nav__item', isActive ? 'argus-shell-nav__item--active' : ''].filter(Boolean).join(' ');
}

export function AdminShell() {
  const t = useT();
  const { locale, setLocale } = useLocale();
  const {
    session,
    accounts,
    units,
    switching,
    isPlatform,
    switchAccount,
    switchUnit,
    signOut,
  } = useSession();
  const [confirmSignOut, setConfirmSignOut] = useState(false);

  if (!session) return null;
  const displayName = session.user.email.split('@')[0] || session.user.email;
  const brandMark = <img src="/brand.svg" alt="" width={24} height={24} />;

  return (
    <AppShell
      brand="ARGUS"
      brandMark={brandMark}
      meta={t('Administração')}
      actions={
        <>
          <ThemeToggle toDarkLabel={t('Mudar para modo escuro')} toLightLabel={t('Mudar para modo claro')} />
          <UserMenu
            name={displayName}
            email={session.user.email}
            locale={locale}
            locales={SUPPORTED_LOCALES.map(code => ({ value: code, label: LOCALE_LABELS[code] }))}
            languageLabel={t('Idioma')}
            logoutLabel={t('Sair')}
            onLocaleChange={next => setLocale(next as typeof locale)}
            onLogout={() => setConfirmSignOut(true)}
          />
        </>
      }
      sidebar={
        <Sidenav brand="ARGUS" brandMark={brandMark} subtitle={t('Administração')} aria-label={t('Contexto da conta')}>
          <div className="argus-sidenav__section argus-admin-context">
            <Select
              label={t('Conta')}
              aria-label={t('Conta ativa')}
              value={session.activeAccount?.id ?? ''}
              disabled={switching}
              onChange={e => void switchAccount(e.target.value || null)}
              options={[
                { value: '', label: t('Nenhuma conta selecionada') },
                ...accounts.map(account => ({ value: account.id, label: account.name })),
              ]}
            />
            {session.activeAccount ? (
              <Select
                label={t('Unidade')}
                aria-label={t('Unidade ativa')}
                value={session.activeUnit?.id ?? ''}
                disabled={switching}
                onChange={e => void switchUnit(e.target.value || null)}
                options={[
                  { value: '', label: t('Nenhuma unidade selecionada') },
                  ...units.map(unit => ({ value: unit.id, label: unit.name })),
                ]}
              />
            ) : null}
            {switching ? (
              <span className="argus-admin-context__pending">
                <Spinner size="sm" label={t('Trocando…')} />
                <span aria-hidden="true">{t('Trocando…')}</span>
              </span>
            ) : null}
          </div>
          <nav className="argus-sidenav__section argus-shell-nav" aria-label={t('Administração')}>
            <NavLink to="/" end className={navClass}>
              {t('Visão geral')}
            </NavLink>
            {session.activeAccount ? (
              <NavLink to="/units" className={navClass}>
                {t('Unidades')}
              </NavLink>
            ) : null}
            {isPlatform ? (
              <>
                <NavLink to="/users" className={navClass}>
                  {t('Usuários')}
                </NavLink>
                <NavLink to="/accounts" className={navClass}>
                  {t('Contas')}
                </NavLink>
              </>
            ) : null}
          </nav>
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
      <Outlet />
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
