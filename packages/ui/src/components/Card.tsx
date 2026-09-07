import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return (
    <section className={`argus-card ${className ?? ''}`.trim()}>
      {children}
    </section>
  );
}
