import { ReactNode } from 'react';

interface ListRowProps {
  title: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
}

export function ListRow({ title, meta, actions }: ListRowProps) {
  return (
    <article className="argus-list-row">
      <div className="argus-list-row__main">
        <div className="argus-list-row__title">{title}</div>
        {meta ? <div className="argus-list-row__meta">{meta}</div> : null}
      </div>
      {actions ? <div className="argus-list-row__actions">{actions}</div> : null}
    </article>
  );
}
