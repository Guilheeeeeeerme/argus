import { useEffect, useState, MouseEvent } from 'react';
import { Button, Input, Card, Message } from '@argus/design-system';
import { call, Location, Camera } from '../api';

interface LocationsProps {
  locations: Location[];
  companyId: string;
  onReload: () => void;
}

export function Locations({ locations, companyId, onReload }: LocationsProps) {
  const [locationName, setLocationName] = useState('New location');
  const [locationAddress, setLocationAddress] = useState('');
  const [openId, setOpenId] = useState<string | null>(null);
  const [message, setMessage] = useState('');

  async function createLocation() {
    try {
      await call(`/v1/companies/${companyId}/locations`, {
        method: 'POST',
        body: JSON.stringify({ name: locationName, address: locationAddress || null, timezone: 'UTC' }),
      });
      onReload();
      setMessage('Location created.');
    } catch (error) {
      setMessage(String(error));
    }
  }

  async function updateLocation(location: Location) {
    const nextName = window.prompt('Location name', location.name);
    if (!nextName) return;
    const nextAddress = window.prompt('Address (used by the agent)', location.address ?? '');
    if (nextAddress === null) return;
    try {
      await call(`/v1/companies/${companyId}/locations/${location.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ name: nextName, address: nextAddress || null, timezone: location.timezone }),
      });
      onReload();
    } catch (error) {
      setMessage(String(error));
    }
  }

  async function deleteLocation(location: Location) {
    if (!window.confirm(`Delete ${location.name}?`)) return;
    try {
      await call(`/v1/companies/${companyId}/locations/${location.id}`, { method: 'DELETE' });
      if (openId === location.id) setOpenId(null);
      onReload();
    } catch (error) {
      setMessage(String(error));
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
          setMessage(`Sketch uploaded for ${location.name}.`);
        } catch (error) {
          setMessage(String(error));
        }
      };
      reader.readAsDataURL(file);
    };
    input.click();
  }

  return (
    <Card>
      <h2>Locations</h2>
      {locations.map(location => (
        <article key={location.id} className="argus-list-item">
          <b>{location.name}</b>
          <span>{location.address ?? 'no address'} · {location.timezone}</span>
          <Button size="sm" variant="ghost" onClick={() => updateLocation(location)}>Edit</Button>
          <Button size="sm" variant="ghost" onClick={() => uploadSketch(location)}>Sketch</Button>
          <Button size="sm" variant="ghost" onClick={() => setOpenId(openId === location.id ? null : location.id)}>
            {openId === location.id ? 'Close plan' : 'Plan'}
          </Button>
          <Button size="sm" variant="danger" onClick={() => deleteLocation(location)}>Delete</Button>
        </article>
      ))}
      {openId && locations.some(l => l.id === openId) && (
        <LocationSketch
          location={locations.find(l => l.id === openId)!}
          companyId={companyId}
          onReload={onReload}
          onMessage={setMessage}
        />
      )}
      <div className="argus-inline-form">
        <Input
          label="Location name"
          value={locationName}
          onChange={e => setLocationName(e.target.value)}
        />
        <Input
          label="Address (agent)"
          value={locationAddress}
          onChange={e => setLocationAddress(e.target.value)}
        />
        <Button onClick={createLocation}>Create location</Button>
      </div>
      <Message text={message} />
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
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [cameraName, setCameraName] = useState('New camera');
  const [streamUrl, setStreamUrl] = useState('rtsp://');
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);

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
      onMessage('Failed to place camera.');
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
      onMessage(String(error));
    }
  }

  return (
    <div className="argus-sketch-editor">
      <div
        className="argus-sketch-canvas"
        onClick={e => {
          if (selectedCamera) void placeCamera(selectedCamera, e);
        }}
        style={{ position: 'relative', minHeight: 240, overflow: 'hidden' }}
      >
        {location.sketch ? (
          <img src={location.sketch} alt={`${location.name} sketch`} style={{ width: '100%', display: 'block' }} />
        ) : (
          <p style={{ padding: 'var(--space-xl)' }}>No sketch uploaded yet.</p>
        )}
        {cameras.map(camera => (
          camera.placement_x != null && camera.placement_y != null ? (
            <span
              key={camera.id}
              className="argus-sketch-marker"
              title={camera.name}
              style={{
                position: 'absolute',
                left: `${camera.placement_x * 100}%`,
                top: `${camera.placement_y * 100}%`,
                transform: 'translate(-50%, -50%)',
                background: 'var(--color-primary, #4a90d9)',
                color: '#fff',
                borderRadius: '50%',
                width: 14,
                height: 14,
                display: 'inline-block',
                cursor: 'pointer',
              }}
            />
          ) : null
        ))}
      </div>
      <div className="argus-inline-form">
        <select
          aria-label="Camera to place"
          onChange={e => setSelectedCamera(cameras.find(c => c.id === e.target.value) ?? null)}
          value={selectedCamera?.id ?? ''}
        >
          <option value="">Select camera…</option>
          {cameras.map(camera => (
            <option key={camera.id} value={camera.id}>
              {camera.name}{camera.placement_x != null ? ' (placed)' : ''}
            </option>
          ))}
        </select>
        <span>Click the sketch to place the selected camera.</span>
      </div>
      <div className="argus-inline-form">
        <Input label="Camera name" value={cameraName} onChange={e => setCameraName(e.target.value)} />
        <Input label="Stream URL (RTSP)" value={streamUrl} onChange={e => setStreamUrl(e.target.value)} />
        <Button onClick={addCamera}>Add camera</Button>
      </div>
    </div>
  );
}
