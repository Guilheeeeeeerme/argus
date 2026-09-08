import { TextareaHTMLAttributes, useId } from 'react';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

export function Textarea({ label, error, id: idProp, className, ...props }: TextareaProps) {
  const generatedId = useId();
  const id = idProp ?? generatedId;
  const errorId = error ? `${id}-error` : undefined;
  const textarea = (
    <textarea
      {...props}
      id={id}
      className={['argus-textarea', className].filter(Boolean).join(' ')}
      aria-invalid={error ? true : undefined}
      aria-describedby={errorId}
    />
  );

  if (!label) {
    return (
      <>
        {textarea}
        {error ? (
          <span id={errorId} className="argus-message argus-message--error" role="alert">
            {error}
          </span>
        ) : null}
      </>
    );
  }

  return (
    <div className="argus-field">
      <label htmlFor={id} className="argus-field__label">
        {label}
      </label>
      {textarea}
      {error ? (
        <span id={errorId} className="argus-message argus-message--error" role="alert">
          {error}
        </span>
      ) : null}
    </div>
  );
}
