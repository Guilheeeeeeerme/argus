import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  as?: 'section' | 'article' | 'div';
}

export function Card({ children, className, as: Tag = 'section' }: CardProps) {
  return <Tag className={['argus-card', className].filter(Boolean).join(' ')}>{children}</Tag>;
}
