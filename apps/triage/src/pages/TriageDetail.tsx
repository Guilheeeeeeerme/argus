import { useEffect, useState } from 'react';
import {
  Badge,
  Button,
  FormSkeleton,
  EmptyState,
  Textarea,
  badgeVariantForTriageState,
  useToast,
} from '@argus/design-system';
import { useT, localizeApiError, triageStateLabel } from '@argus/i18n';
import { useAsync, useMutation } from '@shared/hooks';
import { authedFetch, confidencePercent, getCase, resolveCase, type Disposition, type TriageCaseDetail } from '../api';

interface TriageDetailProps {
  accountId: string;
  caseId: string;
  /** Any operator action inside the detail (resets the FOLLOW idle timer). */
  onInteraction: () => void;
  onResolved: (result: { id: string; state: string; resolved_at: string }) => void;
}

export function TriageDetail({ accountId, caseId, onInteraction, onResolved }: TriageDetailProps) {
  const t = useT();
  const toast = useToast();
  const detail = useAsync(() => getCase(accountId, caseId), [accountId, caseId]);
  const resolve = useMutation((disposition: Disposition, reasoning: string | null) =>
    resolveCase(accountId, caseId, { disposition, reasoning }),
  );
  const [reason, setReason] = useState('');
  const [reasonError, setReasonError] = useState<string | undefined>();
  const [pendingDisposition, setPendingDisposition] = useState<Disposition | null>(null);

  async function submit(disposition: Disposition) {
    onInteraction();
    if (disposition === 'false_positive' && !reason.trim()) {
      setReasonError(t('Justificativa obrigatória para falso positivo.'));
      return;
    }
    setReasonError(undefined);
    setPendingDisposition(disposition);
    const result = await resolve.run(disposition, reason.trim() || null);
    setPendingDisposition(null);
    if (!result.ok) {
      toast.error(localizeApiError(result.error, t));
      return;
    }
    toast.success(t('Caso atualizado.'));
    onResolved({ id: result.data.triage_case_id, state: result.data.state, resolved_at: result.data.resolved_at });
  }

  if (detail.loading && !detail.data) return <FormSkeleton fields={3} label={t('Carregando')} />;
  if (detail.error || !detail.data) {
    return (
      <EmptyState
        title={t('Não foi possível carregar.')}
        description={detail.error ? localizeApiError(detail.error, t) : undefined}
        action={
          <Button variant="secondary" size="sm" onClick={() => void detail.reload()}>
            {t('Tentar novamente')}
          </Button>
        }
      />
    );
  }

  const triageCase = detail.data;
  const detection = triageCase.detection;
  const hits = detection?.prompt_hits ?? [];
  const confidence = confidencePercent(detection?.confidence);
  const isOpen = triageCase.state === 'open';
  const busy = resolve.pending;

  return (
    <div className="argus-triage-detail" onPointerDown={onInteraction} onKeyDown={onInteraction}>
      <p className="argus-triage-detail__state">
        <Badge variant={badgeVariantForTriageState(triageCase.state)}>{triageStateLabel(triageCase.state, t)}</Badge>
        {confidence != null ? (
          <span className="tabular-nums"> · {t('{confidence}% de confiança', { confidence })}</span>
        ) : null}
        {detection?.camera_name ? <span> · {detection.camera_name}</span> : null}
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
                  {hitPct != null ? <span className="tabular-nums"> {hitPct}%</span> : null}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="argus-triage-detail__section">
        <h3>{t('Evidência')}</h3>
        <Evidence detail={triageCase} />
      </section>

      {isOpen ? (
        <>
          <Textarea
            label={t('Justificativa (opcional; recomendada para falso positivo)')}
            value={reason}
            error={reasonError}
            onChange={e => setReason(e.target.value)}
            disabled={busy}
          />
          <div className="argus-resolve-actions">
            <Button variant="ghost" onClick={() => void submit('dismissed')} loading={pendingDisposition === 'dismissed'} disabled={busy}>
              {t('Descartar')}
            </Button>
            <Button
              variant="secondary"
              onClick={() => void submit('false_positive')}
              loading={pendingDisposition === 'false_positive'}
              disabled={busy}
            >
              {t('Falso positivo')}
            </Button>
            <Button variant="primary" onClick={() => void submit('confirmed')} loading={pendingDisposition === 'confirmed'} disabled={busy}>
              {t('Confirmar')}
            </Button>
          </div>
        </>
      ) : null}
    </div>
  );
}

function Evidence({ detail }: { detail: TriageCaseDetail }) {
  const t = useT();
  const clipPath = detail.clip_playback_url ?? null;
  const [clip, setClip] = useState<{ path: string; url: string; isImage: boolean } | null>(null);
  const [clipError, setClipError] = useState(false);

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

  const clipUrl = clip?.path === clipPath ? clip.url : null;
  if (!clipPath) return <p className="argus-list-row__meta">{t('Sem clipe ou frames de evidência.')}</p>;
  if (!clipUrl) {
    return (
      <p className="argus-list-row__meta">
        {t(clipError ? 'Não foi possível carregar o clipe.' : 'Carregando clipe de evidência…')}
      </p>
    );
  }
  return clip?.isImage ? (
    <img className="argus-evidence-media" src={clipUrl} alt={t('Evidência')} />
  ) : (
    <video className="argus-evidence-media" controls preload="metadata" src={clipUrl} />
  );
}
