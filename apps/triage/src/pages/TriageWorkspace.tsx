import { useEffect, useMemo, useState } from 'react';
import {
  AlertDialog,
  AppShell,
  Button,
  Card,
  Drawer,
  EmptyState,
  ThemeToggle,
  UserMenu,
  useToast,
} from '@argus/design-system';
import { useT, useLocale, SUPPORTED_LOCALES, localizeApiError, roleLabel } from '@argus/i18n';
import { useAsync } from '@shared/hooks';
import { clearToken, MAIN_ORIGIN } from '@shared/auth';
import { API, cameraOverview, getToken, listUnits, selectAccount, switchUnit, type Session } from '../api';
import { newestOpen, openCountByCamera } from '../feed';
import { useCaseFeed } from '../hooks/useCaseFeed';
import { CameraGrid } from '../components/CameraGrid';
import { CaseRail } from '../components/CaseRail';
import { UnitPicker } from '../components/UnitPicker';
import { TriageDetail } from './TriageDetail';

interface TriageWorkspaceProps {
  session: Session;
}

const LOCALE_LABELS: Record<(typeof SUPPORTED_LOCALES)[number], string> = {
  en: 'English',
  'pt-BR': 'Português (Brasil)',
};

export function TriageWorkspace({ session: initial }: TriageWorkspaceProps) {
  const t = useT();
  const toast = useToast();
  const { locale, setLocale } = useLocale();
  const [session, setSession] = useState(initial);
  const [switching, setSwitching] = useState(false);
  const [confirmLogout, setConfirmLogout] = useState(false);
  const accountId = session.account_id;
  const unit = session.unit;
  const unitId = unit?.id ?? null;

  const units = useAsync(() => listUnits(accountId), [accountId]);
  const overview = useAsync(() => cameraOverview(accountId, unitId ?? ''), [accountId, unitId], {
    enabled: Boolean(unitId),
  });
  const cameraNames = useMemo(
    () => new Map((overview.data ?? []).map(camera => [camera.id, camera.name])),
    [overview.data],
  );
  const feed = useCaseFeed(accountId, unitId, { cameraNames });
  const { onLiveEvent } = feed;
  const reloadOverview = overview.reload;
  useEffect(() => {
    onLiveEvent(() => void reloadOverview());
    return () => onLiveEvent(null);
  }, [onLiveEvent, reloadOverview]);

  async function changeUnit(nextId: string | null) {
    setSwitching(true);
    try {
      const next = await switchUnit(nextId);
      if (next.ok && 'session' in next) setSession(next.session);
      else if (next.ok) selectAccount();
    } catch (error) {
      toast.error(localizeApiError(error, t));
    } finally {
      setSwitching(false);
    }
  }

  const cases = feed.state.cases;
  const focusedCase = cases.find(item => item.id === feed.state.focusId) ?? null;
  const alertCase = newestOpen(cases);
  const openCounts = useMemo(() => openCountByCamera(cases), [cases]);

  function selectCamera(cameraId: string) {
    feed.touch();
    const target =
      cases.find(item => item.state === 'open' && item.detection?.camera_id === cameraId) ??
      cases.find(item => item.detection?.camera_id === cameraId);
    if (target) feed.dispatch({ type: 'pin', id: target.id });
    else toast.info(t('Sem casos para esta câmera.'));
  }

  function selectCase(id: string) {
    feed.touch();
    feed.dispatch({ type: 'pin', id });
  }

  function closeDrawer() {
    feed.touch();
    feed.dispatch({ type: 'clear_focus' });
  }

  async function logout() {
    try {
      await fetch(`${API}/v1/auth/logout`, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          ...(getToken() ? { authorization: `Bearer ${getToken()}` } : {}),
        },
      });
    } catch {
      /* still clear local session */
    }
    clearToken();
    window.location.assign(MAIN_ORIGIN);
  }

  const displayName = session.email.split('@')[0] || session.email;
  const picker = (
    <UnitPicker
      units={units.data ?? []}
      value={unitId}
      loading={units.loading && !units.data}
      switching={switching}
      onChange={id => void changeUnit(id)}
    />
  );

  return (
    <AppShell
      brand="ARGUS"
      brandMark={<img src="/brand.svg" alt="" width={24} height={24} />}
      meta={`${t('Triagem')} · ${session.account_name}${unit ? ` · ${unit.name}` : ''}`}
      wide
      actions={
        <>
          <Button
            variant="secondary"
            size="sm"
            className="argus-triage-account-switch"
            onClick={selectAccount}
          >
            {t('Trocar de conta')}
          </Button>
          <ThemeToggle toDarkLabel={t('Mudar para modo escuro')} toLightLabel={t('Mudar para modo claro')} />
          <UserMenu
            name={displayName}
            email={session.email}
            locale={locale}
            locales={SUPPORTED_LOCALES.map(code => ({ value: code, label: LOCALE_LABELS[code] }))}
            languageLabel={t('Idioma')}
            logoutLabel={t('Sair')}
            onLocaleChange={next => setLocale(next as typeof locale)}
            onLogout={() => setConfirmLogout(true)}
          />
        </>
      }
    >
      {!unitId ? (
        <div className="argus-triage-pick">
          <Card>
            <EmptyState
              title={t('Selecione uma unidade')}
              description={t(
                units.data && units.data.length === 0
                  ? 'Nenhuma unidade cadastrada nesta conta. Crie uma na administração.'
                  : 'Escolha a unidade cujas câmeras você vai acompanhar.',
              )}
            />
            {picker}
            <div className="argus-triage-pick__actions">
              <Button variant="secondary" size="sm" className="argus-triage-account-switch--compact" onClick={selectAccount}>
                {t('Trocar de conta')}
              </Button>
            </div>
          </Card>
        </div>
      ) : (
        <div className="argus-triage-layout">
          <section className="argus-triage-main" aria-label={t('Câmeras')}>
            <div className="argus-triage-toolbar">
              {picker}
              <div className="argus-triage-toolbar__meta">
                <p className="argus-list-row__meta">{roleLabel(session.role, t)}</p>
                <Button
                  variant="ghost"
                  size="sm"
                  className="argus-triage-account-switch--compact"
                  onClick={selectAccount}
                >
                  {t('Trocar de conta')}
                </Button>
              </div>
            </div>
            <CameraGrid
              accountId={accountId}
              cameras={overview.data}
              loading={overview.loading}
              error={overview.error}
              openCounts={openCounts}
              alertCameraId={alertCase?.state === 'open' ? (alertCase.detection?.camera_id ?? null) : null}
              focusedCameraId={focusedCase?.detection?.camera_id ?? null}
              onRetry={() => void overview.reload()}
              onSelectCamera={selectCamera}
            />
          </section>
          <CaseRail
            cases={cases}
            loading={feed.loading}
            focusId={feed.state.focusId}
            newCount={feed.state.newCount}
            connection={feed.connection}
            onSelect={selectCase}
            onShowNew={() => {
              feed.touch();
              feed.dispatch({ type: 'idle' });
            }}
          />
        </div>
      )}

      <Drawer
        open={focusedCase !== null}
        title={focusedCase?.detection?.camera_name ? `${t('Caso')} · ${focusedCase.detection.camera_name}` : t('Detalhes do caso')}
        description={focusedCase?.detection?.summary ?? undefined}
        size="lg"
        onClose={closeDrawer}
        closeLabel={t('Fechar')}
      >
        {focusedCase ? (
          <TriageDetail
            key={focusedCase.id}
            accountId={accountId}
            caseId={focusedCase.id}
            onInteraction={feed.touch}
            onResolved={result => {
              feed.dispatch({
                type: 'triage_updated',
                id: result.id,
                patch: { state: result.state, resolved_at: result.resolved_at },
              });
              feed.dispatch({ type: 'clear_focus' });
              void overview.reload();
            }}
          />
        ) : null}
      </Drawer>

      <AlertDialog
        open={confirmLogout}
        title={t('Sair?')}
        description={t('Encerrar a sessão neste dispositivo?')}
        confirmLabel={t('Sair')}
        cancelLabel={t('Cancelar')}
        tone="primary"
        onConfirm={() => void logout()}
        onCancel={() => setConfirmLogout(false)}
      />
    </AppShell>
  );
}
