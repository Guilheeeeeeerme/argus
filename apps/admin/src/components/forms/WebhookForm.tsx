import { useState } from 'react';
import { useNavigate, useOutletContext, useParams } from 'react-router';
import {
  Button,
  Drawer,
  EmptyState,
  Form,
  FormError,
  FormSkeleton,
  Input,
  Switch,
  useToast,
} from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { useAsync, useMutation } from '@shared/hooks';
import type { FieldErrors } from '@shared/auth';
import { webhooks as webhooksApi } from '../../api/client';
import type { WebhookEndpoint } from '../../api/types';
import { useCompanyId } from '../../app/SessionProvider';
import { hasFieldErrors, useFieldErrors } from './useFieldErrors';

export interface WebhookFormValues {
  name: string;
  active: boolean;
}

interface WebhookFormProps {
  id: string;
  initial?: WebhookEndpoint | null;
  busy: boolean;
  fieldErrors: FieldErrors;
  formError?: string | null;
  onSubmit: (values: WebhookFormValues) => void;
}

export function WebhookForm({ id, initial, busy, fieldErrors, formError, onSubmit }: WebhookFormProps) {
  const t = useT();
  const [name, setName] = useState(initial?.name ?? '');
  const [active, setActive] = useState(initial?.active ?? true);
  return (
    <Form id={id} busy={busy} onSubmit={() => onSubmit({ name: name.trim(), active })}>
      <FormError message={formError} />
      <Input
        label={t('Nome do webhook')}
        value={name}
        error={fieldErrors.name}
        onChange={e => setName(e.target.value)}
        autoFocus
        required
      />
      <Switch label={t('Webhook ativo')} checked={active} onChange={setActive} disabled={busy} />
    </Form>
  );
}

export interface WebhooksOutletContext {
  unitId: string;
  reload: () => Promise<void>;
  /** Called with the created endpoint (raw token included) so the list can reveal it. */
  onCreated: (endpoint: WebhookEndpoint) => void;
}

/** Route element for `/units/:unitId/webhooks/new` and `/units/:unitId/webhooks/:webhookId/edit`. */
export function WebhookFormDrawer() {
  const t = useT();
  const toast = useToast();
  const navigate = useNavigate();
  const companyId = useCompanyId();
  const { webhookId } = useParams();
  const editing = Boolean(webhookId);
  const { unitId, reload, onCreated } = useOutletContext<WebhooksOutletContext>();

  const record = useAsync(
    () => webhooksApi.list(companyId).then(list => list.find(w => w.id === webhookId) ?? null),
    [companyId, webhookId],
    { enabled: editing },
  );
  const save = useMutation((values: WebhookFormValues) =>
    editing
      ? webhooksApi.update(companyId, webhookId ?? '', values)
      : webhooksApi.create(companyId, { ...values, establishment_id: unitId }),
  );
  const { fieldErrors, setLocalErrors } = useFieldErrors(save.error);

  const close = () => navigate(`/units/${unitId}/webhooks`);

  async function submit(values: WebhookFormValues) {
    const local: FieldErrors = {};
    if (!values.name) local.name = t('Campo obrigatório');
    setLocalErrors(local);
    if (Object.keys(local).length) return;
    const result = await save.run(values);
    if (!result.ok) {
      if (!hasFieldErrors(result.error)) toast.error(localizeApiError(result.error, t));
      return;
    }
    toast.success(editing ? t('Webhook salvo.') : t('Webhook criado. Copie o token agora — ele não será exibido novamente.'));
    void reload();
    if (!editing) onCreated(result.data);
    close();
  }

  const formId = 'webhook-form';
  const notFound = editing && !record.loading && (record.error || !record.data);

  return (
    <Drawer
      open
      title={editing ? t('Editar webhook') : t('Novo webhook')}
      busy={save.pending}
      onClose={close}
      closeLabel={t('Fechar')}
      footer={
        notFound ? (
          <Button variant="ghost" onClick={close}>
            {t('Fechar')}
          </Button>
        ) : (
          <>
            <Button variant="ghost" onClick={close} disabled={save.pending}>
              {t('Cancelar')}
            </Button>
            <Button type="submit" form={formId} loading={save.pending} disabled={editing && record.loading}>
              {save.pending ? t('Salvando…') : editing ? t('Salvar') : t('Criar')}
            </Button>
          </>
        )
      }
    >
      {editing && record.loading ? (
        <FormSkeleton fields={2} label={t('Carregando')} />
      ) : notFound ? (
        <EmptyState title={t('Webhook não encontrado.')} />
      ) : (
        <WebhookForm
          id={formId}
          initial={record.data}
          busy={save.pending}
          fieldErrors={fieldErrors}
          formError={save.error && !hasFieldErrors(save.error) ? localizeApiError(save.error, t) : null}
          onSubmit={values => void submit(values)}
        />
      )}
    </Drawer>
  );
}
