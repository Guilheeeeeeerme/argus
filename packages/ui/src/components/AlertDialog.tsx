import { ReactNode, useEffect, useId, useRef } from 'react';
import { Button } from './Button';

interface AlertDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel: string;
  tone?: 'danger' | 'primary';
  /** Confirm request in flight: confirm shows a spinner, cancel/Escape/backdrop are locked. */
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function AlertDialog({
  open,
  title,
  description,
  confirmLabel,
  cancelLabel,
  tone = 'danger',
  busy = false,
  onConfirm,
  onCancel,
}: AlertDialogProps) {
  const titleId = useId();
  const descId = useId();
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    cancelRef.current?.focus();
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  useEffect(() => {
    if (!open || busy) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCancel();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, busy, onCancel]);

  if (!open) return null;

  return (
    <div
      className="argus-dialog-backdrop"
      role="presentation"
      onMouseDown={e => {
        if (!busy && e.target === e.currentTarget) onCancel();
      }}
    >
      <div
        className="argus-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-busy={busy || undefined}
        aria-labelledby={titleId}
        aria-describedby={descId}
      >
        <h2 id={titleId} className="argus-dialog__title">
          {title}
        </h2>
        <p id={descId} className="argus-dialog__body">
          {description}
        </p>
        <div className="argus-dialog__actions">
          <Button ref={cancelRef} variant="ghost" onClick={onCancel} disabled={busy}>
            {cancelLabel}
          </Button>
          <Button
            variant={tone === 'danger' ? 'danger' : 'primary'}
            onClick={onConfirm}
            loading={busy}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

interface DialogProps {
  open: boolean;
  title: string;
  children: ReactNode;
  /** Request in flight: Escape and backdrop clicks are ignored. */
  busy?: boolean;
  onClose: () => void;
}

export function Dialog({ open, title, children, busy = false, onClose }: DialogProps) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const focusable = panelRef.current?.querySelector<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    focusable?.focus();
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
      previouslyFocused?.focus();
    };
  }, [open]);

  useEffect(() => {
    if (!open || busy) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open, busy, onClose]);

  if (!open) return null;

  return (
    <div
      className="argus-dialog-backdrop"
      role="presentation"
      onMouseDown={e => {
        if (!busy && e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        className="argus-dialog"
        role="dialog"
        aria-modal="true"
        aria-busy={busy || undefined}
        aria-labelledby={titleId}
      >
        <h2 id={titleId} className="argus-dialog__title">
          {title}
        </h2>
        {children}
      </div>
    </div>
  );
}
