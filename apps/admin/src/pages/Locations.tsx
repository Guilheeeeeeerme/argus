import { useEffect, useState, MouseEvent } from 'react';
import {
  Button,
  Input,
  Select,
  Card,
  Message,
  ListRow,
  EmptyState,
  AlertDialog,
  Dialog,
} from '@argus/design-system';
import { useT, localizeApiError } from '@argus/i18n';
import { call, Location, Camera } from '../api';

interface LocationsProps {
  locations: Location[];
  companyId: string;
  onReload: () => void;
}

export function Locations({ locations, companyId, onReload }: LocationsProps) {
  const t = useT();
  const [locationName, setLocationName] = useState('New location');
  const [locationAddress, setLocationAddress] = useState('');
  const [openId, setOpenId] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [pendingDelete, setPendingDelete] = useState<Location | null>(null);
  const [editing, setEditing] = useState<Location | null>(null);
  const [editName, setEditName] = useState('');
  const [editAddress, setEditAddress] = useState('');

  async function createLocation() {
    try {
      await call(`/v1/companies/${companyId}/locations`, {
        method: 'POST',
        body: JSON.stringify({
          name: locationName,
          address: locationAddress || null,
          timezone: 'UTC',
        }),
      });
      onReload();
      setMessage(t('Location created.'));
    } catch (error) {
      setMessage(localizeApiError(String(error), t));
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    const location = pendingDelete;
    setPendingDelete(null);
    try {
      await call(`/v1/companies/${companyId}/locations/${location.id}`, { method: 'DELETE' });
      if (openId === location.id) setOpenId(null);
      onReload();
    } catch (error) {
      setMessage(localizeApiError(String(error), t));
    }
  }

  async function saveEdit() {
    if (!editing || !editName.trim()) return;
    try {
      await call(`/v1/companies/${companyId}/locations/${editing.id}`, {
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

  async function uploadSketch(location: Location) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*,.svg';
    input.onchange = () => {
      const file = input.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          await call(`/v1/companies/${companyId}/locations/${location.id}/sketch`, {
            method: 'PUT',
            body: JSON.stringify({ sketch: String(reader.result) }),
          });
          onReload();
          setMessage(t('Sketch uploaded for {name}.', { name: location.name }));
        } catch (error) {
          setMessage(localizeApiError(String(error), t));
        }
      };
      reader.readAsDataURL(file);
    };
    input.click();
  }

  return (
    <Card>
      <h2>{t('Locations')}</h2>
      {locations.length === 0 ? (
        <EmptyState
          title={t('No locations yet')}
          description={t('Add a location with an optional floor-plan sketch.')}
        />
      ) : (
        locations.map(location => (
          <ListRow
            key={location.id}
            title={location.name}
            meta={`${location.address ?? t('no address')} · ${location.timezone}`}
            actions={
              <>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setEditing(location);
                    setEditName(location.name);
                    setEditAddress(location.address ?? '');
                  }}
                >
                  {t('Edit')}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => void uploadSketch(location)}>
                  {t('Sketch')}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setOpenId(openId === location.id ? null : location.id)}
                >
                  {openId === location.id ? t('Close plan') : t('Plan')}
                </Button>
                <Button size="sm" variant="danger" onClick={() => setPendingDelete(location)}>
                  {t('Delete')}
                </Button>
              </>
            }
          />
        ))
      )}
      {openId && locations.some(l => l.id === openId) ? (
        <LocationSketch
          location={locations.find(l => l.id === openId)!}
          companyId={companyId}
          onReload={onReload}
          onMessage={setMessage}
        />
      ) : null}
      <div className="argus-inline-form">
        <Input
          label={t('Location name')}
          value={locationName}
          onChange={e => setLocationName(e.target.value)}
        />
        <Input
          label={t('Address (agent)')}
          value={locationAddress}
          onChange={e => setLocationAddress(e.target.value)}
        />
        <Button onClick={createLocation}>{t('Create location')}</Button>
      </div>
      <Message text={message} />

      <AlertDialog
        open={Boolean(pendingDelete)}
        title={t('Delete location')}
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
        title={t('Edit location')}
        onClose={() => setEditing(null)}
      >
        <Input
          label={t('Location name')}
          value={editName}
          onChange={e => setEditName(e.target.value)}
        />
        <Input
          label={t('Address (used by the agent)')}
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

function LocationSketch({
  location,
  companyId,
  onReload,
  onMessage,
}: {
  location: Location;
  companyId: string;
  onReload: () => void;
  onMessage: (text: string) => void;
}) {
  const t = useT();
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [cameraName, setCameraName] = useState('New camera');
  const [streamUrl, setStreamUrl] = useState('rtsp://');
  const [selectedCameraId, setSelectedCameraId] = useState('');

  useEffect(() => {
    void (async () => {
      try {
        const all = (await call(`/v1/companies/${companyId}/cameras`)) as Camera[];
        setCameras(all.filter(camera => camera.location_id === location.id));
      } catch {
        /* sketch view is best-effort */
      }
    })();
  }, [companyId, location.id]);

  const selectedCamera = cameras.find(c => c.id === selectedCameraId) ?? null;

  async function placeCamera(camera: Camera, event: MouseEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = Number(((event.clientX - rect.left) / rect.width).toFixed(3));
    const y = Number(((event.clientY - rect.top) / rect.height).toFixed(3));
    try {
      await call(`/v1/companies/${companyId}/cameras/${camera.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          name: camera.name,
          stream_url: camera.stream_url,
          placement_x: x,
          placement_y: y,
        }),
      });
      setCameras(cameras.map(c => (c.id === camera.id ? { ...c, placement_x: x, placement_y: y } : c)));
    } catch {
      onMessage(t('Failed to place camera.'));
    }
  }

  async function addCamera() {
    try {
      await call(`/v1/companies/${companyId}/locations/${location.id}/cameras`, {
        method: 'POST',
        body: JSON.stringify({ name: cameraName, stream_url: streamUrl }),
      });
      const all = (await call(`/v1/companies/${companyId}/cameras`)) as Camera[];
      setCameras(all.filter(camera => camera.location_id === location.id));
      onReload();
    } catch (error) {
      onMessage(localizeApiError(String(error), t));
    }
  }

  return (
    <div className="argus-sketch-editor">
      <div
        className="argus-sketch-canvas"
        role="img"
        aria-label={t('{name} sketch', { name: location.name })}
        onClick={e => {
          if (selectedCamera) void placeCamera(selectedCamera, e);
        }}
      >
        {location.sketch ? (
          <img src={location.sketch} alt={t('{name} sketch', { name: location.name })} />
        ) : (
          <p className="argus-sketch-empty">{t('No sketch uploaded yet.')}</p>
        )}
        {cameras.map(camera =>
          camera.placement_x != null && camera.placement_y != null ? (
            <span
              key={camera.id}
              className="argus-sketch-marker"
              title={camera.name}
              aria-label={camera.name}
              style={{
                left: `${camera.placement_x * 100}%`,
                top: `${camera.placement_y * 100}%`,
              }}
            />
          ) : null,
        )}
      </div>
      <div className="argus-inline-form">
        <Select
          label={t('Camera to place')}
          value={selectedCameraId}
          onChange={e => setSelectedCameraId(e.target.value)}
          options={[
            { value: '', label: t('Select camera…') },
            ...cameras.map(camera => ({
              value: camera.id,
              label: `${camera.name}${camera.placement_x != null ? ` (${t('placed')})` : ''}`,
            })),
          ]}
        />
        <span className="argus-sketch-hint">
          {t('Click the sketch to place the selected camera.')}
        </span>
      </div>
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
        <Button onClick={addCamera}>{t('Add camera')}</Button>
      </div>
    </div>
  );
}
