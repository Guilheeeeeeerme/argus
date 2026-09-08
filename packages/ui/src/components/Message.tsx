interface MessageProps {
  text: string;
  variant?: 'info' | 'error' | 'success';
}

export function Message({ text, variant = 'info' }: MessageProps) {
  if (!text) return <div className="argus-message" aria-live="polite" />;
  return (
    <div
      className={`argus-message argus-message--${variant}`}
      role={variant === 'error' ? 'alert' : 'status'}
      aria-live={variant === 'error' ? 'assertive' : 'polite'}
    >
      {text}
    </div>
  );
}
