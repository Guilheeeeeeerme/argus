import { useEffect, useState } from 'react';
import {
  Card,
  Badge,
  Message,
  ThemeToggle,
  AppShell,
  EmptyState,
  Status,
  Skeleton,
  UserMenu,
  AlertDialog,
  badgeVariantForTriageState,
} from '@argus/design-system';
import { useT, useLocale, SUPPORTED_LOCALES } from '@argus/i18n';
import { clearToken, MAIN_ORIGIN } from '@shared/auth';
import {
  WS,
  Session,
  TriageCase,
  authedFetch,
  getToken,
  redirectToLogin,
  API,
  confidencePercent,
} from '../api';
import { TriageDetail } from './TriageDetail';

interface TriageWorkspaceProps {
  session: Session;
}

const LOCALE_LABELS: Record<(typeof SUPPORTED_LOCALES)[number], string> = {
  en: 'English',
  'pt-BR': 'Português (Brasil)',
};

const LIVE_EVENTS = new Set(['detection.created', 'triage.updated']);

function eventType(raw: string): string | null {
  try {
    const payload = JSON.parse(raw) as { type?: string; event?: string };
    return payload.type ?? payload.event ?? null;
  } catch {
    return null;
  }
}

export function TriageWorkspace({ session }: TriageWorkspaceProps) {
  const t = useT();
  const { locale, setLocale } = useLocale();
  const [cases, setCases] = useState<TriageCase[]>([]);
  const [selected, setSelected] = useState<TriageCase | null>(null);
  const [message, setMessage] = useState('');
  const [connection, setConnection] = useState<'connecting' | 'live' | 'error'>('connecting');
  const [loading, setLoading] = useState(true);
  const [confirmLogout, setConfirmLogout] = useState(false);
  const company = session.company_id;

  useEffect(() => {
    if (!company) return;

    async function loadCases() {
      const response = await authedFetch(`/v1/companies/${company}/triage-cases`);
      if (response.status === 401) {
        redirectToLogin();
        return;
      }
      setCases(await response.json());
      setLoading(false);
      setMessage(t('Live triage connected.'));
    }

    void loadCases();

    const ws = new WebSocket(`${WS}/v1/ws?token=${encodeURIComponent(getToken() ?? '')}`);
    ws.onopen = () => setConnection('live');
    ws.onmessage = event => {
      const type = eventType(String(event.data));
      if (type === 'ready' || type === 'heartbeat') return;
      if (type && !LIVE_EVENTS.has(type)) return;
      authedFetch(`/v1/companies/${company}/triage-cases`)
        .then(x => x.json())
        .then(setCases);
    };
    ws.onerror = () => {
      setConnection('error');
      setMessage(t('WebSocket connection failed.'));
    };
    ws.onclose = () => {
      setConnection('error');
      setMessage(t('WebSocket disconnected; refresh to reconnect.'));
    };

    return () => ws.close();
  }, [company, t]);

  async function selectCase(item: TriageCase) {
    if (!company) return;
    setSelected(
      await authedFetch(`/v1/companies/${company}/triage-cases/${item.id}`).then(r => r.json()),
    );
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

  const where = session.establishment ? session.establishment.name : session.company_name;
  const statusTone = connection === 'live' ? 'live' : connection === 'error' ? 'error' : 'neutral';
  const statusLabel =
    connection === 'live'
      ? t('Live')
      : connection === 'error'
        ? t('Disconnected')
        : t('Connecting…');
  const displayName = session.email.split('@')[0] || session.email;

  return (
    <AppShell
      brand="ARGUS"
      meta={`${t('Triage')} · ${where}`}
      wide
      actions={
        <>
          <ThemeToggle />
          <UserMenu
            name={displayName}
            email={session.email}
            locale={locale}
            locales={SUPPORTED_LOCALES.map(code => ({
              value: code,
              label: LOCALE_LABELS[code],
            }))}
            languageLabel={t('Language')}
            logoutLabel={t('Log out')}
            onLocaleChange={next => setLocale(next as typeof locale)}
            onLogout={() => setConfirmLogout(true)}
          />
        </>
      }
    >
      <div className="argus-triage-status-row">
        <Status label={statusLabel} tone={statusTone} />
        <p className="argus-list-row__meta">{session.role}</p>
      </div>
      <Message text={message} variant={connection === 'error' ? 'error' : 'info'} />
      <div className="argus-triage__grid">
        <Card>
          <h2>{t('Case feed')}</h2>
          {loading ? (
            <div className="argus-skeleton-stack">
              <Skeleton height={36} aria-label={t('Loading cases')} />
              <Skeleton height={36} />
              <Skeleton height={36} />
            </div>
          ) : cases.length === 0 ? (
            <EmptyState
              title={t('No cases yet')}
              description={t('New detections will appear here in real time.')}
            />
          ) : (
            <div className="argus-case-list" role="list">
              {cases.map(item => {
                const confidence = confidencePercent(item.detection?.confidence);
                const label = item.detection?.summary ?? item.id.slice(0, 8);
                return (
                  <button
                    key={item.id}
                    type="button"
                    role="listitem"
                    className="argus-case-btn"
                    aria-current={selected?.id === item.id ? 'true' : undefined}
                    onClick={() => void selectCase(item)}
                  >
                    <Badge variant={badgeVariantForTriageState(item.state)}>{item.state}</Badge>
                    <span className="argus-case-btn__meta">
                      {label}
                      {confidence != null
                        ? ` · ${t('{confidence}% confidence', { confidence })}`
                        : ''}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </Card>
        {selected ? (
          <TriageDetail
            triageCase={selected}
            company={company}
            onResolved={() => {
              setSelected(null);
              setMessage(t('Case updated.'));
              void authedFetch(`/v1/companies/${company}/triage-cases`)
                .then(x => x.json())
                .then(setCases);
            }}
            onClose={() => setSelected(null)}
          />
        ) : (
          <Card>
            <EmptyState
              title={t('Select a case')}
              description={t('Choose an item from the feed to review evidence and resolve.')}
            />
          </Card>
        )}
      </div>

      <AlertDialog
        open={confirmLogout}
        title={t('Log out?')}
        description={t('End your session on this device?')}
        confirmLabel={t('Log out')}
        cancelLabel={t('Cancel')}
        tone="primary"
        onConfirm={() => void logout()}
        onCancel={() => setConfirmLogout(false)}
      />
    </AppShell>
  );
}
