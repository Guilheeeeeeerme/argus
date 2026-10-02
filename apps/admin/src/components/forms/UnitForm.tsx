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
  Select,
  useToast,
} from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { useAsync, useMutation } from '@shared/hooks';
import type { FieldErrors } from '@shared/auth';
import { units as unitsApi } from '../../api/client';
import type { Establishment } from '../../api/types';
import { useCompanyId, useSession } from '../../app/SessionProvider';
import { defaultTimeZone, timeZoneOptions } from '../../lib/timezones';
import { hasFieldErrors, useFieldErrors } from './useFieldErrors';

export interface UnitFormValues {
  name: string;
  address: string;
  timezone: string;
}

interface UnitFormProps {
  id: string;
  initial?: Establishment | null;
  busy: boolean;
  fieldErrors: FieldErrors;
  formError?: string | null;
  onSubmit: (values: UnitFormValues) => void;
}

export function UnitForm({ id, initial, busy, fieldErrors, formError, onSubmit }: UnitFormProps) {
  const t = useT();
  const [name, setName] = useState(initial?.name ?? '');
  const [address, setAddress] = useState(initial?.address ?? '');
  const [timezone, setTimezone] = useState(initial?.timezone ?? defaultTimeZone());

  return (
    <Form id={id} busy={busy} onSubmit={() => onSubmit({ name: name.trim(), address: address.trim(), timezone })}>
      <FormError message={formError} />
      <Input
        label={t('Nome da unidade')}
        value={name}
        error={fieldErrors.name}
        onChange={e => setName(e.target.value)}
        autoFocus
        required
      />
      <Input
        label={t('Endereço')}
        value={address}
        error={fieldErrors.address}
        onChange={e => setAddress(e.target.value)}
      />
      <Select
        label={t('Fuso horário')}
        value={timezone}
        error={fieldErrors.timezone}
        options={timeZoneOptions(timezone)}
        onChange={e => setTimezone(e.target.value)}
      />
    </Form>
  );
}

export interface UnitsOutletContext {
  reload: () => Promise<void>;
}

/** Route element for `/units/new` and `/units/:unitId/edit`. */
export function UnitFormDrawer() {
  const t = useT();
  const toast = useToast();
  const navigate = useNavigate();
  const companyId = useCompanyId();
  const { reloadContext } = useSession();
  const { unitId } = useParams();
  const editing = Boolean(unitId);
  const { reload } = useOutletContext<UnitsOutletContext>();

  const record = useAsync(() => unitsApi.get(companyId, unitId ?? ''), [companyId, unitId], { enabled: editing });
  const save = useMutation((values: UnitFormValues) => {
    const body = { name: values.name, address: values.address || null, timezone: values.timezone };
    return editing ? unitsApi.update(companyId, unitId ?? '', body) : unitsApi.create(companyId, body);
  });
  const { fieldErrors, setLocalErrors } = useFieldErrors(save.error);

  const close = () => navigate('/units');

  async function submit(values: UnitFormValues) {
    const local: FieldErrors = {};
    if (!values.name) local.name = t('Campo obrigatório');
    setLocalErrors(local);
    if (Object.keys(local).length) return;
    const result = await save.run(values);
    if (!result.ok) {
      if (!hasFieldErrors(result.error)) toast.error(localizeApiError(result.error, t));
      return;
    }
    toast.success(editing ? t('Unidade salva.') : t('Unidade criada.'));
    void reload();
    void reloadContext();
    close();
  }

  const formId = 'unit-form';
  const notFound = editing && !record.loading && (record.error || !record.data);

  return (
    <Drawer
      open
      title={editing ? t('Editar unidade') : t('Nova unidade')}
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
        <FormSkeleton fields={3} label={t('Carregando')} />
      ) : notFound ? (
        <EmptyState title={t('Unidade não encontrada.')} />
      ) : (
        <UnitForm
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
