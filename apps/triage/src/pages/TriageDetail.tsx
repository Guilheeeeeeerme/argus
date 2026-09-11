import { useState } from 'react';
import { Button, Textarea, Card, Badge, Message, badgeVariantForTriageState } from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { authedFetch, TriageCase, confidencePercent } from '../api';

interface TriageDetailProps {
  triageCase: TriageCase;
  company: string;
  onResolved: () => void;
  onClose?: () => void;
}

export function TriageDetail({ triageCase, company, onResolved, onClose }: TriageDetailProps) {
  const t = useT();
  const [reason, setReason] = useState('');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function resolve(disposition: 'confirmed' | 'dismissed' | 'false_positive') {
    if (disposition === 'false_positive' && !reason.trim()) {
      setMessage(t('Reasoning is required for false positive.'));
      return;
    }
    setSubmitting(true);
    setMessage('');
    const response = await authedFetch(
      `/v1/companies/${company}/triage-cases/${triageCase.id}/resolve`,
      {
        method: 'POST',
        body: JSON.stringify({
          disposition,
          reasoning: reason.trim() || null,
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

  const detection = triageCase.detection;
  const frames = detection?.frame_uris ?? [];
  const hits = detection?.prompt_hits ?? [];
  const clipUrl = triageCase.clip_playback_url ?? null;
  const confidence = confidencePercent(detection?.confidence);
  const isOpen = triageCase.state === 'open';

  return (
    <Card>
      <h2>{t('Case detail')}</h2>
      <p>
        <Badge variant={badgeVariantForTriageState(triageCase.state)}>{triageCase.state}</Badge>
        {confidence != null ? (
          <>
            {' · '}
            <span className="tabular-nums">
              {t('{confidence}% confidence', { confidence })}
            </span>
          </>
        ) : null}
      </p>

      <section className="argus-triage-detail__section">
        <h3>{t('Summary')}</h3>
        <p>{detection?.summary ?? '—'}</p>
      </section>

      <section className="argus-triage-detail__section">
        <h3>{t('Prompt hits')}</h3>
        {hits.length === 0 ? (
          <p className="argus-list-row__meta">—</p>
        ) : (
          <ul className="argus-prompt-hits">
            {hits.map((hit, index) => {
              const label = hit.name ?? hit.text ?? hit.prompt_id ?? 'prompt';
              const hitPct = confidencePercent(hit.confidence);
              return (
                <li key={hit.prompt_id ?? `${label}-${index}`} className="argus-prompt-hits__row">
                  <Badge variant="open">{label}</Badge>
                  {hitPct != null ? (
                    <span className="tabular-nums"> {hitPct}%</span>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="argus-triage-detail__section">
        <h3>{t('Evidence')}</h3>
        {clipUrl ? (
          <video className="argus-evidence-media" controls preload="metadata" src={clipUrl} />
        ) : null}
        {frames.length > 0 ? (
          <div className="argus-evidence-frames">
            {frames.map(url => (
              <img key={url} src={url} alt="" className="argus-evidence-frame" />
            ))}
          </div>
        ) : null}
        {!clipUrl && frames.length === 0 ? (
          <p className="argus-list-row__meta">{t('No evidence clip or frames.')}</p>
        ) : null}
      </section>

      {isOpen ? (
        <>
          <Textarea
            label={t('Reasoning (optional, recommended for false positive)')}
            value={reason}
            onChange={e => setReason(e.target.value)}
          />
          <div className="argus-resolve-actions">
            {onClose ? (
              <Button variant="ghost" onClick={onClose}>
                {t('Close')}
              </Button>
            ) : null}
            <Button
              variant="ghost"
              onClick={() => void resolve('dismissed')}
              disabled={submitting}
            >
              {t('Dismiss')}
            </Button>
            <Button
              variant="secondary"
              onClick={() => void resolve('false_positive')}
              disabled={submitting}
            >
              {t('False positive')}
            </Button>
            <Button variant="primary" onClick={() => void resolve('confirmed')} disabled={submitting}>
              {t('Confirm')}
            </Button>
          </div>
        </>
      ) : onClose ? (
        <div className="argus-resolve-actions">
          <Button variant="ghost" onClick={onClose}>
            {t('Close')}
          </Button>
        </div>
      ) : null}
      <Message text={message} variant="error" />
    </Card>
  );
}
