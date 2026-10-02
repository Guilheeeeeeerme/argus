import { useState } from 'react';
import {
  Button,
  Dialog,
  Drawer,
  Form,
  FormError,
  Input,
  Switch,
  Textarea,
} from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import type { FieldErrors } from '@shared/auth';
import type { Prompt } from '../../api/types';
import { hasFieldErrors } from './useFieldErrors';

export interface PromptFormValues {
  text: string;
  enabled: boolean;
}

interface PromptDrawerProps {
  open: boolean;
  /** Existing prompt when editing; null for a new one. */
  prompt: Prompt | null;
  busy: boolean;
  error: unknown;
  fieldErrors: FieldErrors;
  onSubmit: (values: PromptFormValues) => void;
  onClose: () => void;
}

/** Drawer with the instruction (prompt) form. Remounts per `prompt` so state resets. */
export function PromptDrawer({ open, prompt, busy, error, fieldErrors, onSubmit, onClose }: PromptDrawerProps) {
  const t = useT();
  const formId = 'prompt-form';
  return (
    <Drawer
      open={open}
      title={prompt ? t('Editar instrução') : t('Nova instrução')}
      description={t('Descreva em linguagem natural o que deve gerar uma detecção positiva.')}
      busy={busy}
      onClose={onClose}
      closeLabel={t('Fechar')}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={busy}>
            {t('Cancelar')}
          </Button>
          <Button type="submit" form={formId} loading={busy}>
            {busy ? t('Salvando…') : prompt ? t('Salvar') : t('Criar')}
          </Button>
        </>
      }
    >
      {open ? (
        <PromptFields
          key={prompt?.id ?? 'new'}
          id={formId}
          initial={prompt}
          busy={busy}
          fieldErrors={fieldErrors}
          formError={error && !hasFieldErrors(error) ? localizeApiError(error, t) : null}
          onSubmit={onSubmit}
        />
      ) : null}
    </Drawer>
  );
}

function PromptFields({
  id,
  initial,
  busy,
  fieldErrors,
  formError,
  onSubmit,
}: {
  id: string;
  initial: Prompt | null;
  busy: boolean;
  fieldErrors: FieldErrors;
  formError: string | null;
  onSubmit: (values: PromptFormValues) => void;
}) {
  const t = useT();
  const [text, setText] = useState(initial?.text ?? '');
  const [enabled, setEnabled] = useState(initial?.enabled ?? true);
  return (
    <Form id={id} busy={busy} onSubmit={() => onSubmit({ text: text.trim(), enabled })}>
      <FormError message={formError} />
      <Textarea
        label={t('Texto da instrução')}
        value={text}
        error={fieldErrors.text}
        onChange={e => setText(e.target.value)}
        rows={5}
        autoFocus
        required
      />
      <Switch label={t('Ativa')} checked={enabled} onChange={setEnabled} disabled={busy} />
    </Form>
  );
}

interface PromptSetNameDialogProps {
  open: boolean;
  title: string;
  initialName: string;
  busy: boolean;
  error: unknown;
  onSubmit: (name: string) => void;
  onClose: () => void;
}

/** Small dialog to create or rename a prompt set with an explicit name. */
export function PromptSetNameDialog({ open, title, initialName, busy, error, onSubmit, onClose }: PromptSetNameDialogProps) {
  return (
    <Dialog open={open} title={title} busy={busy} onClose={onClose}>
      {open ? (
        <PromptSetNameFields
          key={initialName}
          initialName={initialName}
          busy={busy}
          error={error}
          onSubmit={onSubmit}
          onClose={onClose}
        />
      ) : null}
    </Dialog>
  );
}

function PromptSetNameFields({
  initialName,
  busy,
  error,
  onSubmit,
  onClose,
}: Omit<PromptSetNameDialogProps, 'open' | 'title'>) {
  const t = useT();
  const [name, setName] = useState(initialName);
  const [localError, setLocalError] = useState<string | undefined>();
  return (
    <Form
      busy={busy}
      onSubmit={() => {
        const trimmed = name.trim();
        if (!trimmed) {
          setLocalError(t('Campo obrigatório'));
          return;
        }
        setLocalError(undefined);
        onSubmit(trimmed);
      }}
    >
      <FormError message={error ? localizeApiError(error, t) : null} />
      <Input
        label={t('Nome do conjunto')}
        value={name}
        error={localError}
        onChange={e => setName(e.target.value)}
        autoFocus
        required
      />
      <div className="argus-dialog__actions">
        <Button variant="ghost" onClick={onClose} disabled={busy}>
          {t('Cancelar')}
        </Button>
        <Button type="submit" loading={busy}>
          {busy ? t('Salvando…') : t('Salvar')}
        </Button>
      </div>
    </Form>
  );
}
