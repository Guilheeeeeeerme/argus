import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { WS, getToken, listCases, type PromptHit, type TriageCase } from '../api';
import { caseFeedReducer, initialFeedState, FEED_CAPACITY, type FeedAction, type FeedState } from '../feed';
import { useTriageSocket, type SocketEnvelope, type SocketStatus } from './useTriageSocket';

const DEFAULT_IDLE_MS = 120_000;

export function idleTimeoutMs(): number {
  const raw = import.meta.env?.VITE_TRIAGE_IDLE_MS as string | undefined;
  const value = raw ? Number(raw) : NaN;
  return Number.isFinite(value) && value > 0 ? value : DEFAULT_IDLE_MS;
}

export interface CaseFeed {
  state: FeedState;
  dispatch: (action: FeedAction) => void;
  loading: boolean;
  error: unknown;
  connection: SocketStatus;
  reload: () => Promise<void>;
  /** Mark operator interaction (resets the idle timer that restores FOLLOW). */
  touch: () => void;
  /** Called for every live event, after the feed has been updated (overview refresh etc.). */
  onLiveEvent: (listener: (() => void) | null) => void;
}

interface UseCaseFeedOptions {
  /** camera_id → name, so a live row renders with its camera label before any refetch. */
  cameraNames?: ReadonlyMap<string, string>;
  idleMs?: number;
}

export function useCaseFeed(accountId: string, unitId: string | null, options: UseCaseFeedOptions = {}): CaseFeed {
  const [state, dispatch] = useReducer(caseFeedReducer, undefined, initialFeedState);
  const [loading, setLoading] = useState(Boolean(unitId));
  const [error, setError] = useState<unknown>(null);
  const idleMs = options.idleMs ?? idleTimeoutMs();
  const cameraNames = useRef(options.cameraNames);
  cameraNames.current = options.cameraNames;
  const liveListener = useRef<(() => void) | null>(null);
  const idleTimer = useRef<number | undefined>(undefined);
  const requestId = useRef(0);

  const touch = useCallback(() => {
    window.clearTimeout(idleTimer.current);
    idleTimer.current = window.setTimeout(() => dispatch({ type: 'idle' }), idleMs);
  }, [idleMs]);

  useEffect(() => () => window.clearTimeout(idleTimer.current), []);

  const reload = useCallback(async () => {
    if (!unitId) return;
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const cases = await listCases(accountId, { unitId: unitId, state: null, limit: FEED_CAPACITY });
      if (id !== requestId.current) return;
      dispatch({ type: 'loaded', cases });
    } catch (err) {
      if (id !== requestId.current) return;
      setError(err);
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [accountId, unitId]);

  useEffect(() => {
    if (!unitId) {
      dispatch({ type: 'loaded', cases: [] });
      setLoading(false);
      return;
    }
    void reload();
  }, [unitId, reload]);

  const onEnvelope = useCallback(
    (envelope: SocketEnvelope) => {
      const type = envelope.type ?? envelope.event;
      const payload = envelope.payload ?? {};
      if (type === 'detection.created') {
        if (!unitId || payload.unit_id !== unitId) return;
        const cameraId = String(payload.camera_id ?? '');
        const item: TriageCase = {
          id: String(payload.triage_case_id),
          detection_id: String(payload.detection_id),
          state: typeof payload.state === 'string' ? payload.state : 'open',
          updated_at: typeof payload.created_at === 'string' ? payload.created_at : envelope.timestamp ?? null,
          detection: {
            id: String(payload.detection_id),
            camera_id: cameraId,
            unit_id: unitId,
            camera_name: cameraNames.current?.get(cameraId) ?? null,
            sequence_id: typeof payload.sequence_id === 'string' ? payload.sequence_id : null,
            summary: typeof payload.summary === 'string' ? payload.summary : null,
            confidence: typeof payload.confidence === 'number' ? payload.confidence : null,
            prompt_hits: Array.isArray(payload.prompt_hits) ? (payload.prompt_hits as PromptHit[]) : [],
            clip_uri: typeof payload.clip_uri === 'string' ? payload.clip_uri : null,
            created_at: typeof payload.created_at === 'string' ? payload.created_at : envelope.timestamp ?? null,
          },
        };
        dispatch({ type: 'detection_created', case: item });
        liveListener.current?.();
        return;
      }
      if (type === 'triage.updated') {
        dispatch({
          type: 'triage_updated',
          id: String(payload.triage_case_id),
          patch: {
            state: typeof payload.state === 'string' ? payload.state : undefined,
            resolved_at: typeof payload.resolved_at === 'string' ? payload.resolved_at : undefined,
            updated_at: envelope.timestamp ?? undefined,
          },
        });
        liveListener.current?.();
      }
    },
    [unitId],
  );

  const token = getToken();
  const socketUrl = unitId && token ? `${WS}/v1/ws?token=${encodeURIComponent(token)}` : null;
  const connection = useTriageSocket(socketUrl, onEnvelope);

  const onLiveEvent = useCallback((listener: (() => void) | null) => {
    liveListener.current = listener;
  }, []);

  return { state, dispatch, loading, error, connection, reload, touch, onLiveEvent };
}
