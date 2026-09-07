import { InputHTMLAttributes, useId } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export function Input({ label, ...props }: InputProps) {
  const id = useId();
  return (
    <div className="argus-field">
      <label htmlFor={id} className="argus-field__label">{label}</label>
      <input {...props} id={id} className="argus-input" />
    </div>
  );
}
