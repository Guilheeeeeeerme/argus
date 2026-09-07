import { TextareaHTMLAttributes, useId } from 'react';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
}

export function Textarea({ label, ...props }: TextareaProps) {
  const id = useId();
  const textarea = <textarea {...props} id={id} className="argus-textarea" />;

  if (!label) return textarea;

  return (
    <div className="argus-field">
      <label htmlFor={id} className="argus-field__label">{label}</label>
      {textarea}
    </div>
  );
}
