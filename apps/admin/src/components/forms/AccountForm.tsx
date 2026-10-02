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
  useToast,
} from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { useAsync, useMutation } from '@shared/hooks';
import type { FieldErrors } from '@shared/auth';
import { accounts as accountsApi } from '../../api/client';
import type { Company } from '../../api/types';
import { useSession } from '../../app/SessionProvider';
import { hasFieldErrors, useFieldErrors } from './useFieldErrors';

export interface AccountFormValues {
  name: string;
  slug: string;
}

export function slugify(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 63);
}

const SLUG_PATTERN = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/;

interface AccountFormProps {
  id: string;
  initial?: Company | null;
  busy: boolean;
  fieldErrors: FieldErrors;
  formError?: string | null;
  onSubmit: (values: AccountFormValues) => void;
}

export function AccountForm({ id, initial, busy, fieldErrors, formError, onSubmit }: AccountFormProps) {
  const t = useT();
  const [name, setName] = useState(initial?.name ?? '');
  const [slug, setSlug] = useState(initial?.slug ?? '');
  // While creating, the slug follows the name until the user edits it by hand.
  const [slugTouched, setSlugTouched] = useState(Boolean(initial));

  return (
    <Form id={id} busy={busy} onSubmit={() => onSubmit({ name: name.trim(), slug: slug.trim() })}>
      <FormError message={formError} />
      <Input
        label={t('Nome da conta')}
        value={name}
        error={fieldErrors.name}
        onChange={e => {
          setName(e.target.value);
          if (!slugTouched) setSlug(slugify(e.target.value));
        }}
        autoFocus
        required
      />
      <Input
        label={t('Identificador (slug)')}
        value={slug}
        error={fieldErrors.slug}
        onChange={e => {
          setSlugTouched(true);
          setSlug(e.target.value);
        }}
        autoComplete="off"
        spellCheck={false}
        required
      />
      <p className="argus-field__hint argus-form__hint">
        {t('Usado em URLs e integrações. Letras minúsculas, números e hífens.')}
      </p>
    </Form>
  );
}

export interface AccountsOutletContext {
  reload: () => Promise<void>;
}

/** Route element for `/accounts/new` and `/accounts/:accountId/edit`. */
export function AccountFormDrawer() {
  const t = useT();
  const toast = useToast();
  const navigate = useNavigate();
  const { reloadContext } = useSession();
  const { accountId } = useParams();
  const editing = Boolean(accountId);
  const { reload } = useOutletContext<AccountsOutletContext>();

  const record = useAsync(
    () => accountsApi.list().then(list => list.find(c => c.id === accountId) ?? null),
    [accountId],
    { enabled: editing },
  );
  const save = useMutation((values: AccountFormValues) =>
    editing ? accountsApi.update(accountId ?? '', values) : accountsApi.create(values),
  );
  const { fieldErrors, setLocalErrors } = useFieldErrors(save.error);

  const close = () => navigate('/accounts');

  async function submit(values: AccountFormValues) {
    const local: FieldErrors = {};
    if (!values.name) local.name = t('Campo obrigatório');
    if (!values.slug) local.slug = t('Campo obrigatório');
    else if (!SLUG_PATTERN.test(values.slug)) local.slug = t('Use apenas letras minúsculas, números e hífens.');
    setLocalErrors(local);
    if (Object.keys(local).length) return;
    const result = await save.run(values);
    if (!result.ok) {
      if (!hasFieldErrors(result.error)) toast.error(localizeApiError(result.error, t));
      return;
    }
    toast.success(editing ? t('Conta salva.') : t('Conta criada.'));
    void reload();
    void reloadContext();
    close();
  }

  const formId = 'account-form';
  const notFound = editing && !record.loading && (record.error || !record.data);

  return (
    <Drawer
      open
      title={editing ? t('Editar conta') : t('Nova conta')}
      description={t('Empresa, ONG, escola ou universidade que usa o Argus.')}
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
        <EmptyState title={t('Conta não encontrada.')} />
      ) : (
        <AccountForm
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
