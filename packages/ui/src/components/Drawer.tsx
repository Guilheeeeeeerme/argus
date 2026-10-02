import { ReactNode, useEffect, useId, useRef } from 'react';

interface DrawerProps {
  open: boolean;
  title: string;
  description?: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  size?: 'md' | 'lg';
  /** Request in flight: Escape, backdrop and the close button are locked. */
  busy?: boolean;
  /** Accessible label for the close button. */
  closeLabel?: string;
}

const FOCUSABLE =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Side panel for create/edit forms. Full-width below 48rem. */
export function Drawer({
  open,
  title,
  description,
  onClose,
  children,
  footer,
  size = 'md',
  busy = false,
  closeLabel = 'Fechar',
}: DrawerProps) {
  const titleId = useId();
  const descId = useId();
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const body = panelRef.current?.querySelector<HTMLElement>('.argus-drawer__body');
    const first = body?.querySelector<HTMLElement>(FOCUSABLE) ?? panelRef.current?.querySelector<HTMLElement>(FOCUSABLE);
    first?.focus();
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
      previouslyFocused?.focus();
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !busy) {
        onClose();
        return;
      }
      if (e.key !== 'Tab' || !panelRef.current) return;
      const nodes = Array.from(panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (nodes.length === 0) return;
      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, busy, onClose]);

  if (!open) return null;

  return (
    <div
      className="argus-drawer-backdrop"
      role="presentation"
      onMouseDown={e => {
        if (!busy && e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        className={`argus-drawer argus-drawer--${size}`}
        role="dialog"
        aria-modal="true"
        aria-busy={busy || undefined}
        aria-labelledby={titleId}
        aria-describedby={description ? descId : undefined}
      >
        <header className="argus-drawer__header">
          <div className="argus-drawer__heading">
            <h2 id={titleId} className="argus-drawer__title">
              {title}
            </h2>
            {description ? (
              <p id={descId} className="argus-drawer__description">
                {description}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            className="argus-btn argus-btn--ghost argus-btn--sm argus-btn--icon"
            aria-label={closeLabel}
            disabled={busy}
            onClick={onClose}
          >
            <svg className="argus-icon" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </header>
        <div className="argus-drawer__body">{children}</div>
        {footer ? <footer className="argus-drawer__footer">{footer}</footer> : null}
      </div>
    </div>
  );
}
