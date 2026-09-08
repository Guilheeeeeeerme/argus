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
} from '@argus/design-system';
import { useT, useLocale, SUPPORTED_LOCALES } from '@argus/i18n';
import { clearToken, MAIN_ORIGIN } from '@shared/auth';
import { WS, Session, authedFetch, getToken, redirectToLogin, API } from '../api';
import { DecisionDetail } from './DecisionDetail';

interface Decision {
  id: string;
  state: string;
  evidence_count: number;
  cumulative_severity: number;
  updated_at: string;
}

interface TriageWorkspaceProps {
  session: Session;
}

const LOCALE_LABELS: Record<(typeof SUPPORTED_LOCALES)[number], string> = {
  en: 'English',
  'pt-BR': 'Português (Brasil)',
};

export function TriageWorkspace({ session }: TriageWorkspaceProps) {
  const t = useT();
  const { locale, setLocale } = useLocale();
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [selected, setSelected] = useState<Decision | null>(null);
  const [message, setMessage] = useState('');
  const [connection, setConnection] = useState<'connecting' | 'live' | 'error'>('connecting');
  const [loading, setLoading] = useState(true);
  const [confirmLogout, setConfirmLogout] = useState(false);
  const company = session.company_id;

  useEffect(() => {
    if (!company) return;

    async function loadDecisions() {
      const response = await authedFetch(`/v1/companies/${company}/decisions`);
      if (response.status === 401) {
        redirectToLogin();
        return;
      }
      setDecisions(await response.json());
      setLoading(false);
      setMessage(t('Live triage connected.'));
    }

    void loadDecisions();

    const ws = new WebSocket(`${WS}/v1/ws?token=${encodeURIComponent(getToken() ?? '')}`);
    ws.onopen = () => setConnection('live');
    ws.onmessage = () => {
      authedFetch(`/v1/companies/${company}/decisions`)
        .then(x => x.json())
        .then(setDecisions);
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

  async function selectDecision(decision: Decision) {
    if (!company) return;
    setSelected(
      await authedFetch(`/v1/companies/${company}/decisions/${decision.id}`).then(r => r.json()),
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

  const where = session.location ? session.location.name : session.company_name;
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
      <Message
        text={message}
        variant={connection === 'error' ? 'error' : 'info'}
      />
      <div className="argus-triage__grid">
        <Card>
          <h2>{t('Decision feed')}</h2>
          {loading ? (
            <div className="argus-skeleton-stack">
              <Skeleton height={36} aria-label={t('Loading decisions')} />
              <Skeleton height={36} />
              <Skeleton height={36} />
            </div>
          ) : decisions.length === 0 ? (
            <EmptyState
              title={t('No decisions yet')}
              description={t('New detections will appear here in real time.')}
            />
          ) : (
            <div className="argus-decision-list" role="list">
              {decisions.map(decision => (
                <button
                  key={decision.id}
                  type="button"
                  role="listitem"
                  className="argus-decision-btn"
                  aria-current={selected?.id === decision.id ? 'true' : undefined}
                  onClick={() => void selectDecision(decision)}
                >
                  <Badge variant={decision.state as 'normal' | 'weird' | 'warning' | 'resolved'}>
                    {decision.state}
                  </Badge>
                  <span className="argus-decision-btn__meta">
                    {t(
                      decision.evidence_count === 1
                        ? '{count} evidence · severity {severity}'
                        : '{count} evidences · severity {severity}',
                      {
                        count: decision.evidence_count,
                        severity: decision.cumulative_severity,
                      },
                    )}
                  </span>
                </button>
              ))}
            </div>
          )}
        </Card>
        {selected ? (
          <DecisionDetail
            decision={selected}
            company={company}
            onResolved={() => {
              setSelected(null);
              setMessage(t('Decision resolved.'));
            }}
            onClose={() => setSelected(null)}
          />
        ) : (
          <Card>
            <EmptyState
              title={t('Select a decision')}
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
