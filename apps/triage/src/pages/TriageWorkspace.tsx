import { useEffect, useState } from 'react';
import { Button, Card, Header, Badge, Message, ThemeToggle, LocaleToggle } from '@argus/design-system';
import { useT, useLocale } from '@argus/i18n';
import { WS, Session, authedFetch, getToken, redirectToLogin } from '../api';
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

export function TriageWorkspace({ session }: TriageWorkspaceProps) {
  const t = useT();
  const { locale, setLocale } = useLocale();
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [selected, setSelected] = useState<Decision | null>(null);
  const [message, setMessage] = useState('');
  const company = session.company_id;

  useEffect(() => {
    if (!company) return;

    async function loadDecisions() {
      const response = await authedFetch(`/v1/companies/${company}/decisions`);
      if (response.status === 401) { redirectToLogin(); return; }
      setDecisions(await response.json());
      setMessage(t('Live triage connected.'));
    }

    void loadDecisions();

    const ws = new WebSocket(`${WS}/v1/ws?token=${encodeURIComponent(getToken() ?? '')}`);
    ws.onmessage = () => {
      authedFetch(`/v1/companies/${company}/decisions`)
        .then(x => x.json())
        .then(setDecisions);
    };
    ws.onerror = () => setMessage(t('WebSocket connection failed.'));
    ws.onclose = () => setMessage(t('WebSocket disconnected; refresh to reconnect.'));

    return () => ws.close();
  }, [company, t]);

  async function selectDecision(decision: Decision) {
    if (!company) return;
    setSelected(await authedFetch(`/v1/companies/${company}/decisions/${decision.id}`).then(r => r.json()));
  }

  const where = session.location ? session.location.name : session.company_name;

  return (
    <main className="argus-triage">
      <Header
        title="ARGUS Triage"
        subtitle={`${t('Real-time workspace')} · ${session.email} · ${where}`}
        actions={
          <>
            <LocaleToggle locale={locale} label={t('PT-BR')} ariaLabel={t('Switch language')} onLocaleChange={setLocale} />
            <ThemeToggle />
          </>
        }
      />
      <Message text={message} />
      <div className="argus-triage__grid">
        <Card>
          <h2>{t('Decision feed')}</h2>
          {decisions.map(decision => (
            <button
              key={decision.id}
              className="argus-decision-btn"
              onClick={() => selectDecision(decision)}
            >
              <Badge variant={decision.state as any}>{decision.state}</Badge>
              <span>{t(
                decision.evidence_count === 1
                  ? '{count} evidence · severity {severity}'
                  : '{count} evidences · severity {severity}',
                { count: decision.evidence_count, severity: decision.cumulative_severity },
              )}</span>
            </button>
          ))}
        </Card>
        {selected && (
          <DecisionDetail
            decision={selected}
            company={company}
            onResolved={() => { setSelected(null); setMessage(t('Decision resolved.')); }}
          />
        )}
      </div>
    </main>
  );
}
