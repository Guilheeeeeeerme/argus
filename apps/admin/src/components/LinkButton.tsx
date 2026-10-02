import { type ReactNode } from 'react';
import { Link } from 'react-router';

interface LinkButtonProps {
  to: string;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md';
  children: ReactNode;
  className?: string;
}

/** Router `Link` styled as a design-system Button (navigation, never mutations). */
export function LinkButton({ to, variant = 'primary', size = 'md', children, className }: LinkButtonProps) {
  return (
    <Link
      to={to}
      className={['argus-btn', `argus-btn--${variant}`, `argus-btn--${size}`, className].filter(Boolean).join(' ')}
    >
      {children}
    </Link>
  );
}
