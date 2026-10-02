import { useMemo, useState } from 'react';
import { Outlet, useOutletContext } from 'react-router';
import {
  AlertDialog,
  Badge,
  Button,
  Card,
  Dialog,
  EmptyState,
  ListRow,
  ListSkeleton,
  useToast,
} from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { useAsync, useMutation } from '@shared/hooks';
import { webhooks as webhooksApi } from '../../api/client';
import type { WebhookEndpoint } from '../../api/types';
import { useAccountId } from '../../app/SessionProvider';
import { LinkButton } from '../../components/LinkButton';
import { ConfirmDelete } from '../../components/forms/ConfirmDelete';
import { TokenReveal } from '../../components/forms/TokenReveal';
import type { WebhooksOutletContext } from '../../components/forms/WebhookForm';
import type { UnitOutletContext } from '../UnitDetailPage';

export function WebhooksTab() {
  const t = useT();
  const toast = useToast();
  const accountId = useAccountId();
  const { unitId } = useOutletContext<UnitOutletContext>();
  const all = useAsync(() => webhooksApi.list(accountId), [accountId]);
  const endpoints = useMemo(
    () => (all.data ?? []).filter(endpoint => endpoint.unit_id === unitId),
    [all.data, unitId],
  );
  const remove = useMutation((id: string) => webhooksApi.remove(accountId, id));
  const rotate = useMutation((id: string) => webhooksApi.rotate(accountId, id));
  const [pendingDelete, setPendingDelete] = useState<WebhookEndpoint | null>(null);
  const [pendingRotate, setPendingRotate] = useState<WebhookEndpoint | null>(null);
  const [reveal, setReveal] = useState<{ name: string; token: string } | null>(null);

  async function confirmDelete() {
    if (!pendingDelete) return;
    const result = await remove.run(pendingDelete.id);
    if (!result.ok) {
      toast.error(localizeApiError(result.error, t));
      return;
    }
    toast.success(t('Webhook excluído.'));
    setPendingDelete(null);
    void all.reload();
  }

  async function confirmRotate() {
    if (!pendingRotate) return;
    const result = await rotate.run(pendingRotate.id);
    if (!result.ok) {
      toast.error(localizeApiError(result.error, t));
      return;
    }
    toast.success(t('Token rotacionado. Copie o novo token agora.'));
    setPendingRotate(null);
    if (result.data.token) setReveal({ name: result.data.name, token: result.data.token });
  }

  const outletContext: WebhooksOutletContext = {
    unitId,
    reload: all.reload,
    onCreated: endpoint => {
      if (endpoint.token) setReveal({ name: endpoint.name, token: endpoint.token });
    },
  };

  return (
    <>
      <div className="argus-tab-toolbar">
        <p className="argus-tab-toolbar__hint">{t('Webhooks desta unidade recebem eventos externos de contexto.')}</p>
        <LinkButton to="new" size="sm">
          {t('Novo webhook')}
        </LinkButton>
      </div>
      <Card>
        {all.loading && !all.data ? (
          <ListSkeleton rows={2} label={t('Carregando')} />
        ) : all.error ? (
          <EmptyState
            title={t('Não foi possível carregar.')}
            description={localizeApiError(all.error, t)}
            action={
              <Button variant="secondary" size="sm" onClick={() => void all.reload()}>
                {t('Tentar novamente')}
              </Button>
            }
          />
        ) : endpoints.length === 0 ? (
          <EmptyState
            title={t('Nenhum webhook ainda')}
            description={t('Crie um webhook para receber eventos externos.')}
            action={<LinkButton to="new" size="sm">{t('Novo webhook')}</LinkButton>}
          />
        ) : (
          endpoints.map(endpoint => (
            <ListRow
              key={endpoint.id}
              title={endpoint.name}
              meta={endpoint.id}
              actions={
                <>
                  <Badge variant={endpoint.active ? 'normal' : 'neutral'}>
                    {endpoint.active ? t('Ativo') : t('Inativo')}
                  </Badge>
                  <Button size="sm" variant="ghost" onClick={() => setPendingRotate(endpoint)}>
                    {t('Rotacionar token')}
                  </Button>
                  <LinkButton to={`${endpoint.id}/edit`} variant="ghost" size="sm">
                    {t('Editar')}
                  </LinkButton>
                  <Button size="sm" variant="danger" onClick={() => setPendingDelete(endpoint)}>
                    {t('Excluir')}
                  </Button>
                </>
              }
            />
          ))
        )}
      </Card>
      <Outlet context={outletContext} />
      <ConfirmDelete
        open={Boolean(pendingDelete)}
        busy={remove.pending}
        title={t('Excluir webhook')}
        name={pendingDelete?.name ?? ''}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setPendingDelete(null)}
      />
      <AlertDialog
        open={Boolean(pendingRotate)}
        busy={rotate.pending}
        tone="primary"
        title={t('Rotacionar token?')}
        description={t('O token atual deixa de funcionar imediatamente.')}
        confirmLabel={t('Rotacionar token')}
        cancelLabel={t('Cancelar')}
        onConfirm={() => void confirmRotate()}
        onCancel={() => setPendingRotate(null)}
      />
      <Dialog open={reveal !== null} title={reveal?.name ?? ''} onClose={() => setReveal(null)}>
        {reveal ? <TokenReveal token={reveal.token} /> : null}
        <div className="argus-dialog__actions">
          <Button variant="ghost" onClick={() => setReveal(null)}>
            {t('Fechar')}
          </Button>
        </div>
      </Dialog>
    </>
  );
}
