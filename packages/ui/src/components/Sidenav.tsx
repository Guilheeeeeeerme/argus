import { ReactNode } from 'react';

interface SidenavProps {
  children: ReactNode;
  'aria-label'?: string;
}

export function Sidenav({ children, 'aria-label': ariaLabel = 'Context' }: SidenavProps) {
  return (
    <nav className="argus-sidenav" aria-label={ariaLabel}>
      {children}
    </nav>
  );
}
