import { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'danger' | 'ghost';
  size?: 'sm' | 'md';
  children: ReactNode;
}

export function Button({ variant = 'primary', size = 'md', children, ...props }: ButtonProps) {
  const className = [
    'argus-btn',
    `argus-btn--${variant}`,
    `argus-btn--${size}`,
    props.className,
  ].filter(Boolean).join(' ');

  return (
    <button {...props} className={className}>
      {children}
    </button>
  );
}
