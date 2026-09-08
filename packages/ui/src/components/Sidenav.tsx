import { ReactNode } from 'react';

interface SidenavProps {
  children: ReactNode;
  brand?: string;
  subtitle?: string;
  'aria-label'?: string;
}

export function Sidenav({
  children,
  brand,
  subtitle,
  'aria-label': ariaLabel = 'Navigation',
}: SidenavProps) {
  return (
    <div className="argus-sidenav" aria-label={ariaLabel}>
      {(brand || subtitle) && (
        <div className="argus-sidenav__brand">
          {brand ? <p className="argus-sidenav__brand-name">{brand}</p> : null}
          {subtitle ? <h1 className="argus-sidenav__subtitle">{subtitle}</h1> : null}
        </div>
      )}
      <div className="argus-sidenav__body">{children}</div>
    </div>
  );
}
