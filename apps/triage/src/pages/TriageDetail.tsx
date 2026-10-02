import { useEffect, useState } from 'react';
import { Button, Textarea, Card, Badge, Message, badgeVariantForTriageState } from '@argus/design-system';
import { useT, localizeApiError, triageStateLabel } from '@argus/i18n';
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
  const [clip, setClip] = useState<{ path: string; url: string; isImage: boolean } | null>(null);
  const [clipError, setClipError] = useState(false);
  const clipPath = triageCase.clip_playback_url ?? null;

  useEffect(() => {
    const controller = new AbortController();
    let objectUrl: string | null = null;
    setClip(null);
    setClipError(false);
    if (clipPath) {
      void authedFetch(clipPath, { signal: controller.signal })
        .then(async response => {
          if (!response.ok) throw new Error('Evidence request failed');
          const blob = await response.blob();
          if (controller.signal.aborted) return;
          objectUrl = URL.createObjectURL(blob);
          setClip({ path: clipPath, url: objectUrl, isImage: blob.type.startsWith('image/') });
        })
        .catch(() => {
          if (!controller.signal.aborted) setClipError(true);
        });
    }
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [clipPath]);

  async function resolve(disposition: 'confirmed' | 'dismissed' | 'false_positive') {
    if (disposition === 'false_positive' && !reason.trim()) {
      setMessage(t('Justificativa obrigatória para falso positivo.'));
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
  const clipUrl = clip?.path === clipPath ? clip.url : null;
  const confidence = confidencePercent(detection?.confidence);
  const isOpen = triageCase.state === 'open';

  return (
    <Card>
      <h2>{t('Detalhes do caso')}</h2>
      <p>
        <Badge variant={badgeVariantForTriageState(triageCase.state)}>{triageStateLabel(triageCase.state, t)}</Badge>
        {confidence != null ? (
          <>
            {' · '}
            <span className="tabular-nums">
              {t('{confidence}% de confiança', { confidence })}
            </span>
          </>
        ) : null}
      </p>

      <section className="argus-triage-detail__section">
        <h3>{t('Resumo')}</h3>
        <p>{detection?.summary ?? '—'}</p>
      </section>

      <section className="argus-triage-detail__section">
        <h3>{t('Instruções acionadas')}</h3>
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
        <h3>{t('Evidência')}</h3>
        {clipUrl ? (
          clip?.isImage ? (
            <img className="argus-evidence-media" src={clipUrl} alt={t('Evidência')} />
          ) : (
            <video className="argus-evidence-media" controls preload="metadata" src={clipUrl} />
          )
        ) : null}
        {frames.length > 0 ? (
          <div className="argus-evidence-frames">
            {frames.map(url => (
              <img key={url} src={url} alt="" className="argus-evidence-frame" />
            ))}
          </div>
        ) : null}
        {clipPath && !clipUrl ? (
          <p className="argus-list-row__meta">{t(clipError ? 'Não foi possível carregar o clipe.' : 'Carregando clipe de evidência…')}</p>
        ) : null}
        {!clipPath && frames.length === 0 ? (
          <p className="argus-list-row__meta">{t('Sem clipe ou frames de evidência.')}</p>
        ) : null}
      </section>

      {isOpen ? (
        <>
          <Textarea
            label={t('Justificativa (opcional; recomendada para falso positivo)')}
            value={reason}
            onChange={e => setReason(e.target.value)}
          />
          <div className="argus-resolve-actions">
            {onClose ? (
              <Button variant="ghost" onClick={onClose}>
                {t('Fechar')}
              </Button>
            ) : null}
            <Button
              variant="ghost"
              onClick={() => void resolve('dismissed')}
              disabled={submitting}
            >
              {t('Descartar')}
            </Button>
            <Button
              variant="secondary"
              onClick={() => void resolve('false_positive')}
              disabled={submitting}
            >
              {t('Falso positivo')}
            </Button>
            <Button variant="primary" onClick={() => void resolve('confirmed')} disabled={submitting}>
              {t('Confirmar')}
            </Button>
          </div>
        </>
      ) : onClose ? (
        <div className="argus-resolve-actions">
          <Button variant="ghost" onClick={onClose}>
            {t('Fechar')}
          </Button>
        </div>
      ) : null}
      <Message text={message} variant="error" />
    </Card>
  );
}
