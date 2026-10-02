import { FormEvent, FormHTMLAttributes, ReactNode, useId } from 'react';

interface FormProps extends Omit<FormHTMLAttributes<HTMLFormElement>, 'onSubmit'> {
  /** Called after `preventDefault`. Never fires while `busy`, so a double submit sends one request. */
  onSubmit: () => void;
  /** Submission in flight: the whole form is locked. */
  busy?: boolean;
  children: ReactNode;
}

export function Form({ onSubmit, busy = false, children, className, ...props }: FormProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    onSubmit();
  }
  return (
    <form
      {...props}
      noValidate
      className={['argus-form', className].filter(Boolean).join(' ')}
      aria-busy={busy || undefined}
      onSubmit={handleSubmit}
    >
      <fieldset className="argus-form__fieldset" disabled={busy}>
        {children}
      </fieldset>
    </form>
  );
}

interface FormFieldProps {
  label: string;
  /** Id of the control inside; generated when omitted and exposed via render-prop. */
  htmlFor?: string;
  hint?: string;
  error?: string;
  children: ReactNode | ((ids: { id: string; describedBy?: string }) => ReactNode);
}

/** Label + hint + error wrapper for controls that do not carry their own label (Switch groups, custom inputs). */
export function FormField({ label, htmlFor, hint, error, children }: FormFieldProps) {
  const generated = useId();
  const id = htmlFor ?? generated;
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined;
  return (
    <div className="argus-field">
      <label htmlFor={id} className="argus-field__label">
        {label}
      </label>
      {typeof children === 'function' ? children({ id, describedBy }) : children}
      {hint ? (
        <span id={hintId} className="argus-field__hint">
          {hint}
        </span>
      ) : null}
      {error ? (
        <span id={errorId} className="argus-message argus-message--error" role="alert">
          {error}
        </span>
      ) : null}
    </div>
  );
}

interface FormActionsProps {
  children: ReactNode;
  align?: 'end' | 'start' | 'between';
}

export function FormActions({ children, align = 'end' }: FormActionsProps) {
  return <div className={`argus-form__actions argus-form__actions--${align}`}>{children}</div>;
}

interface FormErrorProps {
  message?: string | null;
}

/** Form-level error (non-field). Renders nothing when empty. */
export function FormError({ message }: FormErrorProps) {
  if (!message) return null;
  return (
    <div className="argus-message argus-message--error argus-form__error" role="alert">
      {message}
    </div>
  );
}
