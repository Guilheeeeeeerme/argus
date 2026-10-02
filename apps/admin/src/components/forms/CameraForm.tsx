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
import { cameras as camerasApi, type CameraInput } from '../../api/client';
import type { Camera } from '../../api/types';
import { useAccountId } from '../../app/SessionProvider';
import { hasFieldErrors, useFieldErrors } from './useFieldErrors';

export interface CameraFormValues {
  name: string;
  stream_url: string;
  stream_username: string;
  stream_password: string;
  is_active: boolean;
}

interface CameraFormProps {
  id: string;
  initial?: Camera | null;
  busy: boolean;
  fieldErrors: FieldErrors;
  formError?: string | null;
  onSubmit: (values: CameraFormValues) => void;
}

export function CameraForm({ id, initial, busy, fieldErrors, formError, onSubmit }: CameraFormProps) {
  const t = useT();
  const editing = Boolean(initial);
  const [name, setName] = useState(initial?.name ?? '');
  const [streamUrl, setStreamUrl] = useState(initial?.stream_url ?? '');
  const [username, setUsername] = useState(initial?.stream_username ?? '');
  const [password, setPassword] = useState('');
  const [active, setActive] = useState(initial?.is_active ?? true);

  return (
    <Form
      id={id}
      busy={busy}
      onSubmit={() =>
        onSubmit({
          name: name.trim(),
          stream_url: streamUrl.trim(),
          stream_username: username.trim(),
          stream_password: password,
          is_active: active,
        })
      }
    >
      <FormError message={formError} />
      <Input
        label={t('Nome da câmera')}
        value={name}
        error={fieldErrors.name}
        onChange={e => setName(e.target.value)}
        autoFocus
        required
      />
      <Input
        label={t('URL do stream (RTSP)')}
        value={streamUrl}
        placeholder="rtsp://"
        error={fieldErrors.stream_url}
        onChange={e => setStreamUrl(e.target.value)}
        autoComplete="off"
      />
      <Input
        label={t('Usuário do stream')}
        value={username}
        error={fieldErrors.stream_username}
        onChange={e => setUsername(e.target.value)}
        autoComplete="off"
      />
      <Input
        label={t('Senha do stream')}
        type="password"
        value={password}
        placeholder={editing ? '••••••••' : undefined}
        error={fieldErrors.stream_password}
        onChange={e => setPassword(e.target.value)}
        autoComplete="new-password"
      />
      {editing ? <p className="argus-field__hint argus-form__hint">{t('Deixe em branco para manter a senha atual.')}</p> : null}
      <Switch label={t('Câmera ativa')} checked={active} onChange={setActive} disabled={busy} />
    </Form>
  );
}

export interface CamerasOutletContext {
  unitId: string;
  reload: () => Promise<void>;
}

/** Route element for `/units/:unitId/cameras/new` and `/units/:unitId/cameras/:cameraId/edit`. */
export function CameraFormDrawer() {
  const t = useT();
  const toast = useToast();
  const navigate = useNavigate();
  const accountId = useAccountId();
  const { cameraId } = useParams();
  const editing = Boolean(cameraId);
  const { unitId, reload } = useOutletContext<CamerasOutletContext>();

  const record = useAsync(
    () => camerasApi.list(accountId, unitId, true).then(list => list.find(c => c.id === cameraId) ?? null),
    [accountId, unitId, cameraId],
    { enabled: editing },
  );
  const save = useMutation((values: CameraFormValues) => {
    if (editing) {
      const body: Partial<CameraInput> = {
        name: values.name,
        stream_url: values.stream_url,
        stream_username: values.stream_username,
        is_active: values.is_active,
      };
      if (values.stream_password) body.stream_password = values.stream_password;
      return camerasApi.update(accountId, cameraId ?? '', body);
    }
    return camerasApi.create(accountId, unitId, {
      name: values.name,
      stream_url: values.stream_url || null,
      stream_username: values.stream_username || null,
      stream_password: values.stream_password || null,
      is_active: values.is_active,
    });
  });
  const { fieldErrors, setLocalErrors } = useFieldErrors(save.error);

  const close = () => navigate(`/units/${unitId}/cameras`);

  async function submit(values: CameraFormValues) {
    const local: FieldErrors = {};
    if (!values.name) local.name = t('Campo obrigatório');
    setLocalErrors(local);
    if (Object.keys(local).length) return;
    const result = await save.run(values);
    if (!result.ok) {
      if (!hasFieldErrors(result.error)) toast.error(localizeApiError(result.error, t));
      return;
    }
    toast.success(editing ? t('Câmera salva.') : t('Câmera criada.'));
    void reload();
    close();
  }

  const formId = 'camera-form';
  const notFound = editing && !record.loading && (record.error || !record.data);

  return (
    <Drawer
      open
      title={editing ? t('Editar câmera') : t('Nova câmera')}
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
        <FormSkeleton fields={4} label={t('Carregando')} />
      ) : notFound ? (
        <EmptyState title={t('Câmera não encontrada.')} />
      ) : (
        <CameraForm
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
