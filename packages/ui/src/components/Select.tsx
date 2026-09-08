import { SelectHTMLAttributes, useId } from 'react';

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: SelectOption[];
  error?: string;
}

export function Select({ label, options, error, id: idProp, className, ...props }: SelectProps) {
  const generatedId = useId();
  const id = idProp ?? generatedId;
  const errorId = error ? `${id}-error` : undefined;

  return (
    <div className="argus-field">
      <label htmlFor={id} className="argus-field__label">
        {label}
      </label>
      <select
        {...props}
        id={id}
        className={['argus-select', className].filter(Boolean).join(' ')}
        aria-invalid={error ? true : undefined}
        aria-describedby={errorId}
      >
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error ? (
        <span id={errorId} className="argus-message argus-message--error" role="alert">
          {error}
        </span>
      ) : null}
    </div>
  );
}
