import { ReactNode } from 'react';

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="argus-empty" role="status">
      <p className="argus-empty__title">{title}</p>
      {description ? <p>{description}</p> : null}
      {action}
    </div>
  );
}
