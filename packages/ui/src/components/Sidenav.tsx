import { ReactNode } from 'react';

interface SidenavProps {
  children: ReactNode;
  brand?: string;
  brandMark?: ReactNode;
  subtitle?: string;
  'aria-label'?: string;
}

export function Sidenav({
  children,
  brand,
  brandMark,
  subtitle,
  'aria-label': ariaLabel = 'Navigation',
}: SidenavProps) {
  return (
    <div className="argus-sidenav" aria-label={ariaLabel}>
      {(brand || subtitle || brandMark) && (
        <div className="argus-sidenav__brand">
          {(brandMark || brand) && (
            <div className="argus-sidenav__brand-row">
              {brandMark ? <span className="argus-sidenav__brand-mark">{brandMark}</span> : null}
              {brand ? <p className="argus-sidenav__brand-name">{brand}</p> : null}
            </div>
          )}
          {subtitle ? <h1 className="argus-sidenav__subtitle">{subtitle}</h1> : null}
        </div>
      )}
      <div className="argus-sidenav__body">{children}</div>
    </div>
  );
}
