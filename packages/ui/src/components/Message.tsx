interface MessageProps {
  text: string;
  variant?: 'info' | 'error';
}

export function Message({ text, variant = 'info' }: MessageProps) {
  if (!text) return <div className="argus-message" />;
  return (
    <div className={`argus-message argus-message--${variant}`}>
      {text}
    </div>
  );
}
