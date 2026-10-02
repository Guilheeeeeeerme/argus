import { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  /** Breadcrumb trail, e.g. router links separated by `›`. */
  breadcrumbs?: ReactNode;
  actions?: ReactNode;
  breadcrumbsLabel?: string;
}

export function PageHeader({
  title,
  description,
  breadcrumbs,
  actions,
  breadcrumbsLabel = 'Navegação estrutural',
}: PageHeaderProps) {
  return (
    <div className="argus-page-header">
      {breadcrumbs ? (
        <nav className="argus-page-header__crumbs" aria-label={breadcrumbsLabel}>
          {breadcrumbs}
        </nav>
      ) : null}
      <div className="argus-page-header__row">
        <div className="argus-page-header__heading">
          <h1 className="argus-page-header__title">{title}</h1>
          {description ? <p className="argus-page-header__description">{description}</p> : null}
        </div>
        {actions ? <div className="argus-page-header__actions">{actions}</div> : null}
      </div>
    </div>
  );
}
