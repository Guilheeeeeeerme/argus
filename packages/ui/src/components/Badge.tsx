import { ReactNode } from 'react';

type BadgeVariant = 'normal' | 'weird' | 'warning' | 'resolved' | 'true_positive' | 'false_positive' | 'false_negative';

interface BadgeProps {
  variant: BadgeVariant;
  children: ReactNode;
}

export function Badge({ variant, children }: BadgeProps) {
  return (
    <span className={`argus-badge argus-badge--${variant}`}>
      {children}
    </span>
  );
}
