import { useState } from 'react';
import { useNavigate, useOutletContext, useParams } from 'react-router';
import {
  Button,
  Drawer,
  EmptyState,
  Form,
  FormError,
  FormField,
  FormSkeleton,
  Input,
  Select,
  Switch,
  useToast,
} from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { useAsync, useMutation } from '@shared/hooks';
import type { FieldErrors } from '@shared/auth';
import { users as usersApi, type UserInput } from '../../api/client';
import type { AdminUser, Company } from '../../api/types';
import { useSession } from '../../app/SessionProvider';
import { hasFieldErrors, useFieldErrors } from './useFieldErrors';

export interface UserFormValues {
  email: string;
  role: string;
  password: string;
  company_ids: string[];
}

interface UserFormProps {
  id: string;
  initial?: AdminUser | null;
  companies: Company[];
  busy: boolean;
  fieldErrors: FieldErrors;
  formError?: string | null;
  onSubmit: (values: UserFormValues) => void;
}

export function UserForm({ id, initial, companies, busy, fieldErrors, formError, onSubmit }: UserFormProps) {
  const t = useT();
  const editing = Boolean(initial);
  const [email, setEmail] = useState(initial?.email ?? '');
  const [role, setRole] = useState(initial?.role ?? 'manager');
  const [password, setPassword] = useState('');
  const [companyIds, setCompanyIds] = useState<string[]>(initial?.company_ids ?? []);

  function toggleCompany(companyId: string, next: boolean) {
    setCompanyIds(ids => (next ? [...ids.filter(i => i !== companyId), companyId] : ids.filter(i => i !== companyId)));
  }

  const roleOptions = [
    { value: 'manager', label: t('Gestor') },
    { value: 'operator', label: t('Operador') },
    { value: 'admin', label: t('Administrador') },
  ];
  if (initial?.role === 'root') roleOptions.push({ value: 'root', label: t('Root') });

  return (
    <Form id={id} busy={busy} onSubmit={() => onSubmit({ email: email.trim(), role, password, company_ids: companyIds })}>
      <FormError message={formError} />
      <Input
        label={t('E-mail do usuário')}
        type="email"
        value={email}
        error={fieldErrors.email}
        onChange={e => setEmail(e.target.value)}
        autoComplete="off"
        autoFocus
        required
      />
      <Select
        label={t('Função')}
        value={role}
        error={fieldErrors.role}
        options={roleOptions}
        onChange={e => setRole(e.target.value)}
        disabled={initial?.role === 'root'}
      />
      <Input
        label={editing ? t('Nova senha (opcional)') : t('Senha')}
        type="password"
        value={password}
        error={fieldErrors.password}
        onChange={e => setPassword(e.target.value)}
        autoComplete="new-password"
        required={!editing}
      />
      <FormField label={t('Acesso às contas')} hint={t('Gestores e operadores só veem as contas marcadas.')} error={fieldErrors.company_ids}>
        <div className="argus-switch-list">
          {companies.length === 0 ? (
            <span className="argus-field__hint">{t('Nenhuma conta ainda')}</span>
          ) : (
            companies.map(company => (
              <Switch
                key={company.id}
                size="sm"
                label={company.name}
                checked={companyIds.includes(company.id)}
                onChange={next => toggleCompany(company.id, next)}
                disabled={busy}
              />
            ))
          )}
        </div>
      </FormField>
    </Form>
  );
}

export interface UsersOutletContext {
  companies: Company[];
  reload: () => Promise<void>;
}

/** Route element for `/users/new` and `/users/:userId/edit`. */
export function UserFormDrawer() {
  const t = useT();
  const toast = useToast();
  const navigate = useNavigate();
  const { session } = useSession();
  const { userId } = useParams();
  const editing = Boolean(userId);
  const { companies, reload } = useOutletContext<UsersOutletContext>();

  const record = useAsync(
    () => usersApi.list().then(list => list.find(u => u.id === userId) ?? null),
    [userId],
    { enabled: editing },
  );
  const save = useMutation((values: UserFormValues) => {
    const body: UserInput = { email: values.email, role: values.role, company_ids: values.company_ids };
    if (values.password) body.password = values.password;
    return editing ? usersApi.update(userId ?? '', body) : usersApi.create(body);
  });
  const { fieldErrors, setLocalErrors } = useFieldErrors(save.error);

  const close = () => navigate('/users');

  async function submit(values: UserFormValues) {
    const local: FieldErrors = {};
    if (!values.email) local.email = t('Campo obrigatório');
    if (!editing && !values.password) local.password = t('Campo obrigatório');
    else if (values.password && values.password.length < 8) local.password = t('A senha deve ter pelo menos 8 caracteres.');
    setLocalErrors(local);
    if (Object.keys(local).length) return;
    const result = await save.run(values);
    if (!result.ok) {
      if (!hasFieldErrors(result.error)) toast.error(localizeApiError(result.error, t));
      return;
    }
    toast.success(editing ? t('Usuário salvo.') : t('Usuário criado.'));
    void reload();
    close();
  }

  const formId = 'user-form';
  const isSelf = editing && session?.user.id === userId;
  const notFound = editing && !record.loading && (record.error || !record.data);

  return (
    <Drawer
      open
      title={editing ? t('Editar usuário') : t('Novo usuário')}
      description={isSelf ? t('Você está editando o seu próprio usuário.') : undefined}
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
        <EmptyState title={t('Usuário não encontrado.')} />
      ) : (
        <UserForm
          id={formId}
          initial={record.data}
          companies={companies}
          busy={save.pending}
          fieldErrors={fieldErrors}
          formError={save.error && !hasFieldErrors(save.error) ? localizeApiError(save.error, t) : null}
          onSubmit={values => void submit(values)}
        />
      )}
    </Drawer>
  );
}
