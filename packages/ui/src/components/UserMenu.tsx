import { useEffect, useId, useRef, useState, type ReactNode } from 'react';

export interface UserMenuLocaleOption {
  value: string;
  label: string;
}

export interface UserMenuProps {
  name: string;
  email: string;
  locale: string;
  locales: UserMenuLocaleOption[];
  languageLabel: string;
  logoutLabel: string;
  onLocaleChange: (locale: string) => void;
  onLogout: () => void;
}

export function UserMenu({
  name,
  email,
  locale,
  locales,
  languageLabel,
  logoutLabel,
  onLocaleChange,
  onLogout,
}: UserMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuId = useId();
  const languageId = useId();

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false);
        buttonRef.current?.focus();
      }
    }
    function onPointer(event: PointerEvent) {
      const target = event.target as Node | null;
      if (!target || rootRef.current?.contains(target)) return;
      setOpen(false);
    }
    window.addEventListener('keydown', onKey);
    window.addEventListener('pointerdown', onPointer);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('pointerdown', onPointer);
    };
  }, [open]);

  return (
    <div className="argus-user-menu" ref={rootRef}>
      <button
        ref={buttonRef}
        type="button"
        className="argus-btn argus-btn--ghost argus-btn--sm argus-user-menu__trigger"
        aria-expanded={open}
        aria-haspopup="menu"
        aria-controls={menuId}
        onClick={() => setOpen(value => !value)}
      >
        {name}
      </button>
      {open ? (
        <div id={menuId} role="menu" className="argus-user-menu__panel">
          <div className="argus-user-menu__email">{email}</div>
          <div className="argus-user-menu__section">
            <label className="argus-user-menu__label" htmlFor={languageId}>
              {languageLabel}
            </label>
            <select
              id={languageId}
              className="argus-select argus-user-menu__select"
              value={locale}
              onChange={event => onLocaleChange(event.target.value)}
            >
              {locales.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            role="menuitem"
            className="argus-user-menu__item"
            onClick={() => {
              setOpen(false);
              onLogout();
            }}
          >
            {logoutLabel}
          </button>
        </div>
      ) : null}
    </div>
  );
}

export interface ShellNavItemProps {
  children: ReactNode;
  active?: boolean;
  onClick?: () => void;
  href?: string;
}

export function ShellNavItem({ children, active, onClick, href }: ShellNavItemProps) {
  const className = [
    'argus-shell-nav__item',
    active ? 'argus-shell-nav__item--active' : '',
  ]
    .filter(Boolean)
    .join(' ');

  if (href) {
    return (
      <a className={className} href={href} onClick={onClick}>
        {children}
      </a>
    );
  }

  return (
    <button type="button" className={className} onClick={onClick}>
      {children}
    </button>
  );
}
