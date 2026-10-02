import { useEffect, useState } from 'react';
import { fetchLatestFrame } from '../api';
import { isStale } from '../feed';

export type FrameStatus = 'loading' | 'ok' | 'stale' | 'missing' | 'error';

export interface LatestFrameState {
  url: string | null;
  status: FrameStatus;
  capturedAt: string | null;
}

const DEFAULT_INTERVAL_MS = 2000;
const DEFAULT_TTL_MS = 30_000;

function envNumber(name: string, fallback: number): number {
  const raw = (import.meta.env as Record<string, string | undefined>)?.[name];
  const value = raw ? Number(raw) : NaN;
  return Number.isFinite(value) && value > 0 ? value : fallback;
}

/**
 * Poll a camera's latest frame every ~2 s with ETag revalidation. Blob URLs are
 * revoked on replace/unmount; polling pauses while the tab is hidden.
 */
export function useLatestFrame(accountId: string, cameraId: string, enabled = true): LatestFrameState {
  const [state, setState] = useState<LatestFrameState>({ url: null, status: 'loading', capturedAt: null });

  useEffect(() => {
    if (!enabled) return;
    const intervalMs = envNumber('VITE_LATEST_FRAME_MS', DEFAULT_INTERVAL_MS);
    const ttlMs = envNumber('VITE_LATEST_FRAME_TTL_MS', DEFAULT_TTL_MS);
    let cancelled = false;
    let etag: string | null = null;
    let objectUrl: string | null = null;
    let capturedAt: string | null = null;
    let timer: number | undefined;
    const controller = new AbortController();

    const schedule = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => void tick(), intervalMs);
    };

    async function tick() {
      if (cancelled) return;
      if (document.hidden) {
        schedule();
        return;
      }
      const result = await fetchLatestFrame(accountId, cameraId, etag, controller.signal);
      if (cancelled) return;
      if (result.status === 'ok') {
        if (objectUrl) URL.revokeObjectURL(objectUrl);
        objectUrl = URL.createObjectURL(result.blob);
        etag = result.etag;
        capturedAt = result.capturedAt;
        setState({ url: objectUrl, status: 'ok', capturedAt });
      } else if (result.status === 'not_modified') {
        const stale = isStale(capturedAt, Date.now(), ttlMs);
        setState(current => (current.status === (stale ? 'stale' : 'ok') ? current : { ...current, status: stale ? 'stale' : 'ok' }));
      } else if (result.status === 'missing') {
        etag = null;
        setState(current => (current.status === 'missing' ? current : { ...current, status: 'missing' }));
      } else {
        setState(current => (current.status === 'error' ? current : { ...current, status: 'error' }));
      }
      schedule();
    }

    const onVisible = () => {
      if (!document.hidden) {
        window.clearTimeout(timer);
        void tick();
      }
    };
    document.addEventListener('visibilitychange', onVisible);
    void tick();

    return () => {
      cancelled = true;
      controller.abort();
      window.clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisible);
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [accountId, cameraId, enabled]);

  return state;
}
