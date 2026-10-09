import { ReactNode, useEffect, useId, useState } from 'react';

interface AppShellProps {
  brand: string;
  brandMark?: ReactNode;
  meta?: string;
  actions?: ReactNode;
  sidebar?: ReactNode;
  children: ReactNode;
  wide?: boolean;
  /** Accessible label for the mobile menu open control. */
  menuOpenLabel?: string;
  /** Accessible label for closing the mobile menu (button + backdrop). */
  menuCloseLabel?: string;
}

export function AppShell({
  brand,
  brandMark,
  meta,
  actions,
  sidebar,
  children,
  wide,
  menuOpenLabel = 'Abrir menu',
  menuCloseLabel = 'Fechar menu',
}: AppShellProps) {
  const [navOpen, setNavOpen] = useState(false);
  const navId = useId();

  useEffect(() => {
    if (!navOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setNavOpen(false);
    };
    // Permanent sidebar from 64rem; below that the drawer is phone + tablet portrait.
    const mq = window.matchMedia('(min-width: 64rem)');
    const onMq = () => {
      if (mq.matches) setNavOpen(false);
    };
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    document.addEventListener('keydown', onKey);
    mq.addEventListener('change', onMq);
    return () => {
      document.body.style.overflow = prevOverflow;
      document.removeEventListener('keydown', onKey);
      mq.removeEventListener('change', onMq);
    };
  }, [navOpen]);

  return (
    <div
      className={[
        'argus-shell',
        sidebar ? 'argus-shell--with-sidebar' : '',
        navOpen ? 'argus-shell--nav-open' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {sidebar ? (
        <>
          <button
            type="button"
            className="argus-shell__nav-backdrop"
            tabIndex={navOpen ? 0 : -1}
            aria-hidden={!navOpen}
            aria-label={menuCloseLabel}
            onClick={() => setNavOpen(false)}
          />
          <aside
            id={navId}
            className="argus-shell__sidebar"
            onClick={event => {
              const target = event.target as HTMLElement | null;
              if (target?.closest('a.argus-shell-nav__item')) setNavOpen(false);
            }}
          >
            {sidebar}
          </aside>
        </>
      ) : null}
      <div className="argus-shell__column">
        <header className="argus-shell__top">
          <div className="argus-shell__brand">
            {sidebar ? (
              <button
                type="button"
                className="argus-btn argus-btn--ghost argus-btn--sm argus-btn--icon argus-shell__menu-btn"
                aria-expanded={navOpen}
                aria-controls={navId}
                aria-label={navOpen ? menuCloseLabel : menuOpenLabel}
                onClick={() => setNavOpen(value => !value)}
              >
                {navOpen ? (
                  <svg className="argus-icon" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                    <path
                      d="M4 4l8 8M12 4l-8 8"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                    />
                  </svg>
                ) : (
                  <svg className="argus-icon" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                    <path
                      d="M2.5 4.5h11M2.5 8h11M2.5 11.5h11"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                    />
                  </svg>
                )}
              </button>
            ) : null}
            {brandMark ? <span className="argus-shell__brand-mark">{brandMark}</span> : null}
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
