import { useEffect, useMemo, useState } from 'react';
import { useOutletContext, useSearchParams } from 'react-router';
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ListRow,
  ListSkeleton,
  Select,
  Switch,
  useToast,
} from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { useAsync, useMutation } from '@shared/hooks';
import { cameras as camerasApi, promptSets as promptSetsApi, prompts as promptsApi } from '../../api/client';
import type { Prompt, PromptSet } from '../../api/types';
import { useAccountId } from '../../app/SessionProvider';
import { ConfirmDelete } from '../../components/forms/ConfirmDelete';
import { PromptDrawer, PromptSetNameDialog, type PromptFormValues } from '../../components/forms/PromptForm';
import { useFieldErrors, hasFieldErrors } from '../../components/forms/useFieldErrors';
import type { UnitOutletContext } from '../UnitDetailPage';

type Editor = { mode: 'new' } | { mode: 'edit'; prompt: Prompt } | null;
type SetDialog = { mode: 'create' } | { mode: 'rename'; set: PromptSet } | null;

export function PromptsTab() {
  const t = useT();
  const toast = useToast();
  const accountId = useAccountId();
  const { unitId } = useOutletContext<UnitOutletContext>();
  const [params, setParams] = useSearchParams();

  const cameras = useAsync(() => camerasApi.list(accountId, unitId, true), [accountId, unitId]);
  const cameraId = params.get('camera') ?? '';

  useEffect(() => {
    if (!cameraId && cameras.data && cameras.data.length > 0) {
      setParams({ camera: cameras.data[0].id }, { replace: true });
    }
  }, [cameraId, cameras.data, setParams]);

  const sets = useAsync(
    () => promptSetsApi.list(accountId, cameraId),
    [accountId, cameraId],
    { enabled: Boolean(cameraId) },
  );
  const setId = params.get('set') ?? '';
  const activeSet = useMemo(() => {
    if (!sets.data || sets.data.length === 0) return null;
    return sets.data.find(s => s.id === setId) ?? sets.data[0];
  }, [sets.data, setId]);

  const [editor, setEditor] = useState<Editor>(null);
  const [setDialog, setSetDialog] = useState<SetDialog>(null);
  const [pendingDelete, setPendingDelete] = useState<Prompt | null>(null);
  const [pendingSetDelete, setPendingSetDelete] = useState<PromptSet | null>(null);
  const [togglingIds, setTogglingIds] = useState<ReadonlySet<string>>(new Set());

  const savePrompt = useMutation((values: PromptFormValues) => {
    if (editor?.mode === 'edit') return promptsApi.update(accountId, editor.prompt.id, values);
    if (!activeSet) throw new Error('No prompt set');
    return promptsApi.create(accountId, activeSet.id, { ...values, sort_order: activeSet.prompts.length });
  });
  const { fieldErrors, setLocalErrors } = useFieldErrors(savePrompt.error);
  const removePrompt = useMutation((id: string) => promptsApi.remove(accountId, id));
  const saveSet = useMutation((name: string) =>
    setDialog?.mode === 'rename'
      ? promptSetsApi.rename(accountId, setDialog.set.id, name)
      : promptSetsApi.create(accountId, cameraId, name),
  );
  const removeSet = useMutation((id: string) => promptSetsApi.remove(accountId, id));

  function selectCamera(id: string) {
    setParams(id ? { camera: id } : {}, { replace: true });
  }

  async function submitPrompt(values: PromptFormValues) {
    if (!values.text) {
      setLocalErrors({ text: t('Campo obrigatório') });
      return;
    }
    setLocalErrors({});
    const result = await savePrompt.run(values);
    if (!result.ok) {
      if (!hasFieldErrors(result.error)) toast.error(localizeApiError(result.error, t));
      return;
    }
    toast.success(editor?.mode === 'edit' ? t('Instrução salva.') : t('Instrução criada.'));
    setEditor(null);
    void sets.reload();
  }

  async function toggleEnabled(prompt: Prompt, next: boolean) {
    if (togglingIds.has(prompt.id)) return;
    setTogglingIds(ids => new Set(ids).add(prompt.id));
    try {
      await promptsApi.update(accountId, prompt.id, { enabled: next });
      toast.success(next ? t('Instrução ativada.') : t('Instrução desativada.'));
      sets.setData(list =>
        list?.map(s => ({
          ...s,
          prompts: s.prompts.map(p => (p.id === prompt.id ? { ...p, enabled: next } : p)),
        })) ?? list,
      );
    } catch (error) {
      toast.error(localizeApiError(error, t));
    } finally {
      setTogglingIds(ids => {
        const copy = new Set(ids);
        copy.delete(prompt.id);
        return copy;
      });
    }
  }

  async function confirmDeletePrompt() {
    if (!pendingDelete) return;
    const result = await removePrompt.run(pendingDelete.id);
    if (!result.ok) {
      toast.error(localizeApiError(result.error, t));
      return;
    }
    toast.success(t('Instrução excluída.'));
    setPendingDelete(null);
    void sets.reload();
  }

  async function submitSet(name: string) {
    const result = await saveSet.run(name);
    if (!result.ok) return;
    toast.success(setDialog?.mode === 'rename' ? t('Conjunto salvo.') : t('Conjunto criado.'));
    setSetDialog(null);
    await sets.reload();
    if (result.data?.id) setParams({ camera: cameraId, set: result.data.id }, { replace: true });
  }

  async function confirmDeleteSet() {
    if (!pendingSetDelete) return;
    const result = await removeSet.run(pendingSetDelete.id);
    if (!result.ok) {
      toast.error(localizeApiError(result.error, t));
      return;
    }
    toast.success(t('Conjunto excluído.'));
    setPendingSetDelete(null);
    setParams({ camera: cameraId }, { replace: true });
    void sets.reload();
  }

  const cameraOptions = (cameras.data ?? []).map(c => ({
    value: c.id,
    label: c.is_active ? c.name : `${c.name} (${t('Inativa').toLowerCase()})`,
  }));
  const prompts = activeSet ? [...activeSet.prompts].sort((a, b) => a.sort_order - b.sort_order) : [];

  return (
    <>
      <div className="argus-tab-toolbar argus-tab-toolbar--stack">
        <div className="argus-tab-toolbar__field">
          <Select
            label={t('Câmera')}
            value={cameraId}
            disabled={cameras.loading && !cameras.data}
            options={cameraOptions.length ? cameraOptions : [{ value: '', label: t('Nenhuma câmera ainda') }]}
            onChange={e => selectCamera(e.target.value)}
          />
        </div>
        {sets.data && sets.data.length > 1 ? (
          <div className="argus-tab-toolbar__field">
            <Select
              label={t('Conjunto')}
              value={activeSet?.id ?? ''}
              options={sets.data.map(s => ({ value: s.id, label: s.name }))}
              onChange={e => setParams({ camera: cameraId, set: e.target.value }, { replace: true })}
            />
          </div>
        ) : null}
      </div>

      {!cameraId ? (
        cameras.loading ? (
          <ListSkeleton rows={2} label={t('Carregando')} />
        ) : (
          <EmptyState
            title={t('Selecione uma câmera')}
            description={t(
              cameras.data?.length ? 'Escolha uma câmera para ver suas instruções.' : 'Adicione uma câmera com a URL RTSP do stream.',
            )}
          />
        )
      ) : sets.loading && !sets.data ? (
        <Card>
          <ListSkeleton rows={3} label={t('Carregando')} />
        </Card>
      ) : sets.error ? (
        <EmptyState
          title={t('Não foi possível carregar.')}
          description={localizeApiError(sets.error, t)}
          action={
            <Button variant="secondary" size="sm" onClick={() => void sets.reload()}>
              {t('Tentar novamente')}
            </Button>
          }
        />
      ) : !activeSet ? (
        <EmptyState
          title={t('Nenhum conjunto de instruções ainda')}
          description={t('Crie um conjunto para começar a adicionar instruções.')}
          action={
            <Button size="sm" onClick={() => setSetDialog({ mode: 'create' })}>
              {t('Novo conjunto de instruções')}
            </Button>
          }
        />
      ) : (
        <Card>
          <div className="argus-card-head">
            <h2>{activeSet.name}</h2>
            <div className="argus-card-head__actions">
              <Button size="sm" variant="ghost" onClick={() => setSetDialog({ mode: 'rename', set: activeSet })}>
                {t('Renomear conjunto')}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setSetDialog({ mode: 'create' })}>
                {t('Novo conjunto de instruções')}
              </Button>
              <Button size="sm" variant="danger" onClick={() => setPendingSetDelete(activeSet)}>
                {t('Excluir conjunto')}
              </Button>
              <Button size="sm" onClick={() => setEditor({ mode: 'new' })}>
                {t('Nova instrução')}
              </Button>
            </div>
          </div>
          {prompts.length === 0 ? (
            <EmptyState
              title={t('Nenhuma instrução ainda')}
              description={t('Adicione instruções que definem detecções positivas.')}
              action={
                <Button size="sm" onClick={() => setEditor({ mode: 'new' })}>
                  {t('Nova instrução')}
                </Button>
              }
            />
          ) : (
            prompts.map(prompt => (
              <ListRow
                key={prompt.id}
                title={prompt.text}
                actions={
                  <>
                    <Badge variant={prompt.enabled ? 'normal' : 'neutral'}>
                      {prompt.enabled ? t('Ativa') : t('Inativa')}
                    </Badge>
                    <Switch
                      size="sm"
                      hideLabel
                      label={t('Ativa')}
                      checked={prompt.enabled}
                      loading={togglingIds.has(prompt.id)}
                      onChange={next => void toggleEnabled(prompt, next)}
                    />
                    <Button size="sm" variant="ghost" onClick={() => setEditor({ mode: 'edit', prompt })}>
                      {t('Editar')}
                    </Button>
                    <Button size="sm" variant="danger" onClick={() => setPendingDelete(prompt)}>
                      {t('Excluir')}
                    </Button>
                  </>
                }
              />
            ))
          )}
        </Card>
      )}

      <PromptDrawer
        open={editor !== null}
        prompt={editor?.mode === 'edit' ? editor.prompt : null}
        busy={savePrompt.pending}
        error={savePrompt.error}
        fieldErrors={fieldErrors}
        onSubmit={values => void submitPrompt(values)}
        onClose={() => {
          setEditor(null);
          savePrompt.reset();
          setLocalErrors({});
        }}
      />
      <PromptSetNameDialog
        open={setDialog !== null}
        title={setDialog?.mode === 'rename' ? t('Renomear conjunto') : t('Novo conjunto de instruções')}
        initialName={setDialog?.mode === 'rename' ? setDialog.set.name : ''}
        busy={saveSet.pending}
        error={saveSet.error}
        onSubmit={name => void submitSet(name)}
        onClose={() => {
          setSetDialog(null);
          saveSet.reset();
        }}
      />
      <ConfirmDelete
        open={Boolean(pendingDelete)}
        busy={removePrompt.pending}
        title={t('Excluir instrução')}
        name={pendingDelete ? pendingDelete.text.slice(0, 60) : ''}
        onConfirm={() => void confirmDeletePrompt()}
        onCancel={() => setPendingDelete(null)}
      />
      <ConfirmDelete
        open={Boolean(pendingSetDelete)}
        busy={removeSet.pending}
        title={t('Excluir conjunto')}
        name={pendingSetDelete?.name ?? ''}
        onConfirm={() => void confirmDeleteSet()}
        onCancel={() => setPendingSetDelete(null)}
      />
    </>
  );
}
