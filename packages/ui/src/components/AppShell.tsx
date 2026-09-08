import { ReactNode } from 'react';

interface AppShellProps {
  brand: string;
  meta?: string;
  actions?: ReactNode;
  sidebar?: ReactNode;
  children: ReactNode;
  wide?: boolean;
}

export function AppShell({
  brand,
  meta,
  actions,
  sidebar,
  children,
  wide,
}: AppShellProps) {
  return (
    <div className={['argus-shell', sidebar ? 'argus-shell--with-sidebar' : ''].filter(Boolean).join(' ')}>
      {sidebar ? <aside className="argus-shell__sidebar">{sidebar}</aside> : null}
      <div className="argus-shell__column">
        <header className="argus-shell__top">
          <div className="argus-shell__brand">
            <span className="argus-shell__brand-name">{brand}</span>
            {meta ? <span className="argus-shell__brand-meta">{meta}</span> : null}
          </div>
          {actions ? <div className="argus-shell__actions">{actions}</div> : null}
        </header>
        <main
          className={['argus-shell__body', wide ? 'argus-shell__body--wide' : '']
            .filter(Boolean)
            .join(' ')}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
