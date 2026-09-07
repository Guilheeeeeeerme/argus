import { SelectHTMLAttributes, useId } from 'react';

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: SelectOption[];
}

export function Select({ label, options, ...props }: SelectProps) {
  const id = useId();
  return (
    <div className="argus-field">
      <label htmlFor={id} className="argus-field__label">{label}</label>
      <select {...props} id={id} className="argus-select">
        {options.map(opt => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  );
}
