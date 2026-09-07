import { ReactNode } from 'react';

interface SidenavProps {
  children: ReactNode;
}

export function Sidenav({ children }: SidenavProps) {
  return (
    <nav className="argus-sidenav">
      {children}
    </nav>
  );
}
