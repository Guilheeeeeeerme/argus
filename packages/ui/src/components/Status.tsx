interface StatusProps {
  label: string;
  tone?: 'neutral' | 'live' | 'error';
}

export function Status({ label, tone = 'neutral' }: StatusProps) {
  const className =
    tone === 'live'
      ? 'argus-status argus-status--live'
      : tone === 'error'
        ? 'argus-status argus-status--error'
        : 'argus-status';

  return (
    <span className={className} role="status">
      <span className="argus-status__dot" aria-hidden="true" />
      {label}
    </span>
  );
}
