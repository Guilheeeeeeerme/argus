import { DependencyList, useCallback, useEffect, useRef, useState } from 'react';

export interface AsyncState<T> {
  data: T | null;
  /** True while the first load or a `reload()` is in flight. Previous `data` stays available during reloads. */
  loading: boolean;
  error: unknown;
  reload: () => Promise<void>;
  /** Local update without a refetch (optimistic edits, removing a deleted row). */
  setData: (updater: T | null | ((current: T | null) => T | null)) => void;
}

interface UseAsyncOptions {
  /** When false the fetch is skipped and `data` is null. */
  enabled?: boolean;
}

/**
 * Run an async read whenever `deps` change. Stale responses are discarded, so a
 * fast context switch never overwrites newer data.
 */
export function useAsync<T>(
  fn: () => Promise<T>,
  deps: DependencyList,
  { enabled = true }: UseAsyncOptions = {},
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<unknown>(null);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const requestId = useRef(0);

  const run = useCallback(async () => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);
    try {
      const result = await fnRef.current();
      if (id !== requestId.current) return;
      setData(result);
    } catch (err) {
      if (id !== requestId.current) return;
      setError(err);
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) {
      requestId.current++;
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }
    void run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, run, ...deps]);

  return { data, loading, error, reload: run, setData };
}

export type MutationResult<R> = { ok: true; data: R } | { ok: false; error: unknown };

export interface Mutation<A extends unknown[], R> {
  /**
   * Execute the mutation. Calls made while one is already pending return the
   * in-flight result instead of sending a second request. Never throws.
   */
  run: (...args: A) => Promise<MutationResult<R>>;
  pending: boolean;
  error: unknown;
  reset: () => void;
}

export function useMutation<A extends unknown[], R>(fn: (...args: A) => Promise<R>): Mutation<A, R> {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  const inFlight = useRef<Promise<MutationResult<R>> | null>(null);

  const run = useCallback(async (...args: A): Promise<MutationResult<R>> => {
    if (inFlight.current) return inFlight.current;
    setPending(true);
    setError(null);
    const promise = (async (): Promise<MutationResult<R>> => {
      try {
        const data = await fnRef.current(...args);
        return { ok: true, data };
      } catch (err) {
        setError(err);
        return { ok: false, error: err };
      } finally {
        inFlight.current = null;
        setPending(false);
      }
    })();
    inFlight.current = promise;
    return promise;
  }, []);

  const reset = useCallback(() => setError(null), []);

  return { run, pending, error, reset };
}
