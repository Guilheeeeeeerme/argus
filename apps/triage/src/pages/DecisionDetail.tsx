import { useState } from 'react';
import { Button, Select, Textarea, Card, Badge, Message } from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { authedFetch } from '../api';

interface Evidence {
  id: string;
  severity_score: number;
  captured_at: string;
  vlm_result?: { reasoning?: string; description?: string };
}

interface Decision {
  id: string;
  state: string;
  evidence_count: number;
  cumulative_severity: number;
  updated_at: string;
  evidences?: Evidence[];
}

interface DecisionDetailProps {
  decision: Decision;
  company: string;
  onResolved: () => void;
  onClose?: () => void;
}

export function DecisionDetail({ decision, company, onResolved, onClose }: DecisionDetailProps) {
  const t = useT();
  const [state, setState] = useState('');
  const [reason, setReason] = useState('');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function resolve() {
    setSubmitting(true);
    const response = await authedFetch(
      `/v1/companies/${company}/decisions/${decision.id}/resolve`,
      {
        method: 'POST',
        body: JSON.stringify({
          disposition: state,
          reasoning: reason,
          updated_at: decision.updated_at,
        }),
      },
    );
    setSubmitting(false);
    if (response.ok) {
      onResolved();
    } else {
      setMessage(localizeApiError(await response.text(), t));
    }
  }

  return (
    <Card>
      <h2>{t('Decision detail')}</h2>
      <p>
        <Badge variant={decision.state as 'normal' | 'weird' | 'warning' | 'resolved'}>
          {decision.state}
        </Badge>
        {' · '}
        <span className="tabular-nums">
          {t('{count} evidences', { count: decision.evidence_count })}
        </span>
      </p>
      {decision.evidences?.map((evidence: Evidence) => (
        <article key={evidence.id} className="argus-evidence">
          <div className="argus-evidence__header">
            <b className="argus-evidence__score">{evidence.severity_score}</b>
            <span className="argus-evidence__time">
              {new Date(evidence.captured_at).toLocaleString()}
            </span>
          </div>
          <p>{evidence.vlm_result?.reasoning ?? evidence.vlm_result?.description}</p>
        </article>
      ))}
      <Select
        label={t('Disposition')}
        value={state}
        onChange={e => setState(e.target.value)}
        options={[
          { value: '', label: t('Select…') },
          { value: 'true_positive', label: t('True Positive') },
          { value: 'false_positive', label: t('False Positive') },
          { value: 'false_negative', label: t('False Negative') },
        ]}
      />
      <Textarea
        label={t('Reasoning (required for false positive/negative)')}
        value={reason}
        onChange={e => setReason(e.target.value)}
      />
      <div className="argus-resolve-actions">
        {onClose ? (
          <Button variant="ghost" onClick={onClose}>
            {t('Close')}
          </Button>
        ) : null}
        <Button onClick={() => void resolve()} disabled={!state || submitting}>
          {t('Resolve')}
        </Button>
      </div>
      <Message text={message} variant="error" />
    </Card>
  );
}
