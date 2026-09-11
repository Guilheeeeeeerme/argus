import { useEffect, useState } from 'react';
import {
  Button,
  Input,
  Textarea,
  Card,
  Message,
  ListRow,
  EmptyState,
  AlertDialog,
  Dialog,
  Badge,
} from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { call, Establishment, Camera, Prompt, PromptSet } from '../api';

interface EstablishmentsProps {
  establishments: Establishment[];
  companyId: string;
  onReload: () => void;
}

export function Establishments({ establishments, companyId, onReload }: EstablishmentsProps) {
  const t = useT();
  const [name, setName] = useState('New establishment');
  const [address, setAddress] = useState('');
  const [openId, setOpenId] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [pendingDelete, setPendingDelete] = useState<Establishment | null>(null);
  const [editing, setEditing] = useState<Establishment | null>(null);
  const [editName, setEditName] = useState('');
  const [editAddress, setEditAddress] = useState('');

  async function createEstablishment() {
    try {
      await call(`/v1/companies/${companyId}/establishments`, {
        method: 'POST',
        body: JSON.stringify({
          name,
          address: address || null,
          timezone: 'UTC',
        }),
      });
      onReload();
      setMessage(t('Establishment created.'));
    } catch (error) {
      setMessage(localizeApiError(String(error), t));
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    const establishment = pendingDelete;
    setPendingDelete(null);
    try {
      await call(`/v1/companies/${companyId}/establishments/${establishment.id}`, {
        method: 'DELETE',
      });
      if (openId === establishment.id) setOpenId(null);
      onReload();
    } catch (error) {
      setMessage(localizeApiError(String(error), t));
    }
  }

  async function saveEdit() {
    if (!editing || !editName.trim()) return;
    try {
      await call(`/v1/companies/${companyId}/establishments/${editing.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          name: editName.trim(),
          address: editAddress || null,
          timezone: editing.timezone,
        }),
      });
      setEditing(null);
      onReload();
    } catch (error) {
      setMessage(localizeApiError(String(error), t));
    }
  }

  return (
    <Card>
      <h2>{t('Establishments')}</h2>
      {establishments.length === 0 ? (
        <EmptyState
          title={t('No establishments yet')}
          description={t('Add an establishment, then manage its cameras and prompts.')}
        />
      ) : (
        establishments.map(establishment => (
          <ListRow
            key={establishment.id}
            title={establishment.name}
            meta={`${establishment.address ?? t('no address')} · ${establishment.timezone}`}
            actions={
              <>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setEditing(establishment);
                    setEditName(establishment.name);
                    setEditAddress(establishment.address ?? '');
                  }}
                >
                  {t('Edit')}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setOpenId(openId === establishment.id ? null : establishment.id)}
                >
                  {openId === establishment.id ? t('Close cameras') : t('Cameras')}
                </Button>
                <Button size="sm" variant="danger" onClick={() => setPendingDelete(establishment)}>
                  {t('Delete')}
                </Button>
              </>
            }
          />
        ))
      )}
      {openId && establishments.some(e => e.id === openId) ? (
        <EstablishmentDetail
          establishment={establishments.find(e => e.id === openId)!}
          companyId={companyId}
          onReload={onReload}
          onMessage={setMessage}
        />
      ) : null}
      <div className="argus-inline-form">
        <Input
          label={t('Establishment name')}
          value={name}
          onChange={e => setName(e.target.value)}
        />
        <Input label={t('Address')} value={address} onChange={e => setAddress(e.target.value)} />
        <Button onClick={createEstablishment}>{t('Create establishment')}</Button>
      </div>
      <Message text={message} />

      <AlertDialog
        open={Boolean(pendingDelete)}
        title={t('Delete establishment')}
        description={t('Delete {name}? This cannot be undone.', {
          name: pendingDelete?.name ?? '',
        })}
        confirmLabel={t('Delete')}
        cancelLabel={t('Cancel')}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setPendingDelete(null)}
      />

      <Dialog
        open={Boolean(editing)}
        title={t('Edit establishment')}
        onClose={() => setEditing(null)}
      >
        <Input
          label={t('Establishment name')}
          value={editName}
          onChange={e => setEditName(e.target.value)}
        />
        <Input
          label={t('Address')}
          value={editAddress}
          onChange={e => setEditAddress(e.target.value)}
        />
        <div className="argus-dialog__actions">
          <Button variant="ghost" onClick={() => setEditing(null)}>
            {t('Cancel')}
          </Button>
          <Button onClick={() => void saveEdit()}>{t('Save')}</Button>
        </div>
      </Dialog>
    </Card>
  );
}

function EstablishmentDetail({
  establishment,
  companyId,
  onReload,
  onMessage,
}: {
  establishment: Establishment;
  companyId: string;
  onReload: () => void;
  onMessage: (text: string) => void;
}) {
  const t = useT();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null);
  const [promptSet, setPromptSet] = useState<PromptSet | null>(null);
  const [cameraName, setCameraName] = useState('New camera');
  const [streamUrl, setStreamUrl] = useState('rtsp://');
  const [promptText, setPromptText] = useState('');
  const [editingPrompt, setEditingPrompt] = useState<Prompt | null>(null);
  const [editPromptText, setEditPromptText] = useState('');

  async function reloadCameras() {
    try {
      const list = (await call(
        `/v1/companies/${companyId}/establishments/${establishment.id}/cameras`,
      )) as Camera[];
      setCameras(list);
      if (selectedCameraId && !list.some(c => c.id === selectedCameraId)) {
        setSelectedCameraId(null);
        setPromptSet(null);
      }
    } catch {
      setCameras([]);
    }
  }

  async function reloadPromptSet(cameraId: string) {
    try {
      const sets = (await call(
        `/v1/companies/${companyId}/cameras/${cameraId}/prompt-sets`,
      )) as PromptSet[];
      setPromptSet(sets[0] ?? null);
    } catch {
      setPromptSet(null);
    }
  }

  useEffect(() => {
    void reloadCameras();
  }, [companyId, establishment.id]);

  useEffect(() => {
    if (selectedCameraId) void reloadPromptSet(selectedCameraId);
    else setPromptSet(null);
  }, [companyId, selectedCameraId]);

  async function addCamera() {
    try {
      const created = (await call(
        `/v1/companies/${companyId}/establishments/${establishment.id}/cameras`,
        {
          method: 'POST',
          body: JSON.stringify({ name: cameraName, stream_url: streamUrl }),
        },
      )) as Camera;
      await reloadCameras();
      setSelectedCameraId(created.id);
      onReload();
    } catch (error) {
      onMessage(localizeApiError(String(error), t));
    }
  }

  async function ensurePromptSet(): Promise<PromptSet | null> {
    if (promptSet) return promptSet;
    if (!selectedCameraId) return null;
    try {
      const created = (await call(
        `/v1/companies/${companyId}/cameras/${selectedCameraId}/prompt-sets`,
        {
          method: 'POST',
          body: JSON.stringify({ name: 'Default', prompts: [] }),
        },
      )) as PromptSet;
      setPromptSet(created);
      return created;
    } catch (error) {
      onMessage(localizeApiError(String(error), t));
      return null;
    }
  }

  async function addPrompt() {
    if (!promptText.trim()) return;
    const set = await ensurePromptSet();
    if (!set) return;
    try {
      await call(`/v1/companies/${companyId}/prompt-sets/${set.id}/prompts`, {
        method: 'POST',
        body: JSON.stringify({ text: promptText.trim(), enabled: true }),
      });
      setPromptText('');
      onMessage(t('Prompt created.'));
      await reloadPromptSet(selectedCameraId!);
    } catch (error) {
      onMessage(localizeApiError(String(error), t));
    }
  }

  async function savePromptEdit() {
    if (!editingPrompt || !editPromptText.trim()) return;
    try {
      await call(`/v1/companies/${companyId}/prompts/${editingPrompt.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ text: editPromptText.trim(), enabled: editingPrompt.enabled }),
      });
      setEditingPrompt(null);
      onMessage(t('Prompt saved.'));
      if (selectedCameraId) await reloadPromptSet(selectedCameraId);
    } catch (error) {
      onMessage(localizeApiError(String(error), t));
    }
  }

  async function togglePrompt(prompt: Prompt) {
    try {
      await call(`/v1/companies/${companyId}/prompts/${prompt.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ enabled: !prompt.enabled }),
      });
      if (selectedCameraId) await reloadPromptSet(selectedCameraId);
    } catch (error) {
      onMessage(localizeApiError(String(error), t));
    }
  }

  const prompts = promptSet?.prompts ?? [];
  const selectedCamera = cameras.find(c => c.id === selectedCameraId) ?? null;

  return (
    <div className="argus-establishment-detail">
      <h3>{t('Cameras · {name}', { name: establishment.name })}</h3>
      {cameras.length === 0 ? (
        <EmptyState
          title={t('No cameras yet')}
          description={t('Add a camera with an RTSP stream URL.')}
        />
      ) : (
        cameras.map(camera => (
          <ListRow
            key={camera.id}
            title={camera.name}
            meta={camera.stream_url ?? '—'}
            actions={
              <>
                <Badge variant={camera.is_active ? 'normal' : 'neutral'}>
                  {camera.is_active ? t('Enabled') : t('Disabled')}
                </Badge>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() =>
                    setSelectedCameraId(selectedCameraId === camera.id ? null : camera.id)
                  }
                >
                  {selectedCameraId === camera.id ? t('Close') : t('Prompts')}
                </Button>
              </>
            }
          />
        ))
      )}
      <div className="argus-inline-form">
        <Input
          label={t('Camera name')}
          value={cameraName}
          onChange={e => setCameraName(e.target.value)}
        />
        <Input
          label={t('Stream URL (RTSP)')}
          value={streamUrl}
          onChange={e => setStreamUrl(e.target.value)}
        />
        <Button onClick={() => void addCamera()}>{t('Add camera')}</Button>
      </div>

      {selectedCamera ? (
        <>
          <h3>
            {t('Prompt set')} · {selectedCamera.name}
          </h3>
          {prompts.length === 0 ? (
            <EmptyState
              title={t('No prompts yet')}
              description={t('Add prompts that define positive detections.')}
            />
          ) : (
            prompts.map(prompt => (
              <ListRow
                key={prompt.id}
                title={prompt.text.slice(0, 60) || prompt.id.slice(0, 8)}
                meta={prompt.text}
                actions={
                  <>
                    <Badge variant={prompt.enabled ? 'normal' : 'neutral'}>
                      {prompt.enabled ? t('Enabled') : t('Disabled')}
                    </Badge>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setEditingPrompt(prompt);
                        setEditPromptText(prompt.text);
                      }}
                    >
                      {t('Edit')}
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => void togglePrompt(prompt)}>
                      {prompt.enabled ? t('Disable') : t('Enable')}
                    </Button>
                  </>
                }
              />
            ))
          )}
          <div className="argus-inline-form argus-inline-form--stack">
            <Textarea
              label={t('Prompt body')}
              value={promptText}
              onChange={e => setPromptText(e.target.value)}
            />
            <Button onClick={() => void addPrompt()}>{t('Add prompt')}</Button>
          </div>
        </>
      ) : null}

      <Dialog
        open={Boolean(editingPrompt)}
        title={t('Edit prompt')}
        onClose={() => setEditingPrompt(null)}
      >
        <Textarea
          label={t('Prompt body')}
          value={editPromptText}
          onChange={e => setEditPromptText(e.target.value)}
        />
        <div className="argus-dialog__actions">
          <Button variant="ghost" onClick={() => setEditingPrompt(null)}>
            {t('Cancel')}
          </Button>
          <Button onClick={() => void savePromptEdit()}>{t('Save')}</Button>
        </div>
      </Dialog>
    </div>
  );
}
