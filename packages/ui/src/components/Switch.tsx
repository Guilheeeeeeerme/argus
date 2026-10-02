import { useId } from 'react';
import { Spinner } from './Spinner';

interface SwitchProps {
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
  description?: string;
  disabled?: boolean;
  /** Toggle request in flight: locked, `aria-busy`, spinner beside the control. */
  loading?: boolean;
  /** Visually hide the label (it stays available to assistive tech). */
  hideLabel?: boolean;
  size?: 'sm' | 'md';
}

export function Switch({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  loading = false,
  hideLabel = false,
  size = 'md',
}: SwitchProps) {
  const labelId = useId();
  const descId = useId();
  const locked = disabled || loading;
  return (
    <div className={['argus-switch', `argus-switch--${size}`, locked ? 'argus-switch--locked' : ''].filter(Boolean).join(' ')}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-labelledby={labelId}
        aria-describedby={description ? descId : undefined}
        aria-busy={loading || undefined}
        disabled={locked}
        className="argus-switch__control"
        onClick={() => onChange(!checked)}
      >
        <span className="argus-switch__thumb" aria-hidden="true" />
      </button>
      {loading ? <Spinner size="sm" className="argus-switch__spinner" /> : null}
      <span className="argus-switch__text">
        <span id={labelId} className={hideLabel ? 'sr-only' : 'argus-switch__label'}>
          {label}
        </span>
        {description ? (
          <span id={descId} className="argus-switch__description">
            {description}
          </span>
        ) : null}
      </span>
    </div>
  );
}
