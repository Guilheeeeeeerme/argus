import { InputHTMLAttributes, useId } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export function Input({ label, error, id: idProp, className, ...props }: InputProps) {
  const generatedId = useId();
  const id = idProp ?? generatedId;
  const errorId = error ? `${id}-error` : undefined;

  return (
    <div className="argus-field">
      <label htmlFor={id} className="argus-field__label">
        {label}
      </label>
      <input
        {...props}
        id={id}
        className={['argus-input', className].filter(Boolean).join(' ')}
        aria-invalid={error ? true : undefined}
        aria-describedby={errorId}
      />
      {error ? (
        <span id={errorId} className="argus-message argus-message--error" role="alert">
          {error}
        </span>
      ) : null}
    </div>
  );
}
