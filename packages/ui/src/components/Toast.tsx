import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

export type ToastVariant = 'success' | 'error' | 'info';

export interface ToastOptions {
  /** Auto-dismiss delay in ms. Defaults to 5000. */
  duration?: number;
}

interface ToastItem {
  id: number;
  variant: ToastVariant;
  message: string;
  duration: number;
}

export interface ToastApi {
  toast: (variant: ToastVariant, message: string, options?: ToastOptions) => number;
  success: (message: string, options?: ToastOptions) => number;
  error: (message: string, options?: ToastOptions) => number;
  info: (message: string, options?: ToastOptions) => number;
  dismiss: (id: number) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const MAX_VISIBLE = 3;
const DEFAULT_DURATION = 5000;

interface ToastProviderProps {
  children: ReactNode;
  /** Accessible label for the per-toast close button. */
  closeLabel?: string;
}

export function ToastProvider({ children, closeLabel = 'Fechar' }: ToastProviderProps) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setItems(current => current.filter(item => item.id !== id));
  }, []);

  const toast = useCallback(
    (variant: ToastVariant, message: string, options?: ToastOptions) => {
      const id = nextId.current++;
      setItems(current => {
        const next = [...current, { id, variant, message, duration: options?.duration ?? DEFAULT_DURATION }];
        return next.length > MAX_VISIBLE ? next.slice(next.length - MAX_VISIBLE) : next;
      });
      return id;
    },
    [],
  );

  const api = useMemo<ToastApi>(
    () => ({
      toast,
      success: (message, options) => toast('success', message, options),
      error: (message, options) => toast('error', message, options),
      info: (message, options) => toast('info', message, options),
      dismiss,
    }),
    [toast, dismiss],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="argus-toaster" aria-label="Notificações">
        {items.map(item => (
          <ToastView key={item.id} item={item} closeLabel={closeLabel} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastView({
  item,
  closeLabel,
  onDismiss,
}: {
  item: ToastItem;
  closeLabel: string;
  onDismiss: (id: number) => void;
}) {
  const timer = useRef<number | undefined>(undefined);

  const clear = useCallback(() => {
    if (timer.current !== undefined) {
      window.clearTimeout(timer.current);
      timer.current = undefined;
    }
  }, []);

  const start = useCallback(() => {
    clear();
    timer.current = window.setTimeout(() => onDismiss(item.id), item.duration);
  }, [clear, item.duration, item.id, onDismiss]);

  useEffect(() => {
    start();
    return clear;
  }, [start, clear]);

  const isError = item.variant === 'error';
  return (
    <div
      className={`argus-toast argus-toast--${item.variant}`}
      role={isError ? 'alert' : 'status'}
      aria-live={isError ? 'assertive' : 'polite'}
      onMouseEnter={clear}
      onMouseLeave={start}
      onFocus={clear}
      onBlur={start}
    >
      <span className="argus-toast__message">{item.message}</span>
      <button
        type="button"
        className="argus-toast__close"
        aria-label={closeLabel}
        onClick={() => onDismiss(item.id)}
      >
        <svg className="argus-icon" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
