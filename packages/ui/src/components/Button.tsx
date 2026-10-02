import { ButtonHTMLAttributes, ReactNode, forwardRef } from 'react';
import { Spinner } from './Spinner';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md';
  /** Pending mutation: disables the button, sets `aria-busy` and shows a spinner before the label. */
  loading?: boolean;
  children: ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = 'primary',
    size = 'md',
    loading = false,
    disabled,
    children,
    className,
    type = 'button',
    ...props
  },
  ref,
) {
  const classes = [
    'argus-btn',
    `argus-btn--${variant}`,
    `argus-btn--${size}`,
    loading ? 'argus-btn--loading' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      ref={ref}
      type={type}
      {...props}
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
    >
      {loading ? <Spinner size="sm" /> : null}
      {children}
    </button>
  );
});
