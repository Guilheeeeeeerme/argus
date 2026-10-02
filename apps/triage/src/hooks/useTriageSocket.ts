import { useEffect, useRef, useState } from 'react';
import { backoffDelay } from '../feed';

export type SocketStatus = 'connecting' | 'live' | 'reconnecting' | 'closed';

/** Close codes the server uses for auth failures; reconnecting would only loop. */
const FATAL_CLOSE_CODES = new Set([4001, 4003]);

export interface SocketEnvelope {
  type?: string;
  event?: string;
  timestamp?: string;
  payload?: Record<string, unknown>;
}

/**
 * WebSocket with exponential-backoff reconnection. `url === null` keeps it closed.
 * The latest `onMessage` is always used, so callers need not memoise it.
 */
export function useTriageSocket(url: string | null, onMessage: (envelope: SocketEnvelope) => void): SocketStatus {
  const [status, setStatus] = useState<SocketStatus>(url ? 'connecting' : 'closed');
  const handler = useRef(onMessage);
  handler.current = onMessage;

  useEffect(() => {
    if (!url) {
      setStatus('closed');
      return;
    }
    let disposed = false;
    let socket: WebSocket | null = null;
    let timer: number | undefined;
    let attempt = 0;

    function connect() {
      if (disposed) return;
      setStatus(attempt === 0 ? 'connecting' : 'reconnecting');
      socket = new WebSocket(url as string);
      socket.onopen = () => {
        attempt = 0;
        setStatus('live');
      };
      socket.onmessage = event => {
        let envelope: SocketEnvelope;
        try {
          envelope = JSON.parse(String(event.data)) as SocketEnvelope;
        } catch {
          return;
        }
        handler.current(envelope);
      };
      socket.onclose = event => {
        if (disposed) return;
        if (FATAL_CLOSE_CODES.has(event.code)) {
          setStatus('closed');
          return;
        }
        setStatus('reconnecting');
        timer = window.setTimeout(() => {
          attempt += 1;
          connect();
        }, backoffDelay(attempt));
      };
      socket.onerror = () => {
        /* onclose follows and schedules the retry */
      };
    }

    connect();
    return () => {
      disposed = true;
      window.clearTimeout(timer);
      socket?.close();
    };
  }, [url]);

  return status;
}
