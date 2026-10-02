import { KeyboardEvent, MouseEvent, ReactNode } from 'react';

export interface TabItem {
  id: string;
  label: ReactNode;
  /** When set, the tab renders as a link so deep links and middle-click work; `onChange` still fires. */
  href?: string;
}

interface TabsProps {
  tabs: TabItem[];
  value: string;
  onChange: (id: string) => void;
  'aria-label': string;
}

/** Controlled tab list with roving focus (arrow keys, Home, End). Panels are rendered by the caller. */
export function Tabs({ tabs, value, onChange, 'aria-label': ariaLabel }: TabsProps) {
  function onKeyDown(event: KeyboardEvent<HTMLElement>, index: number) {
    const last = tabs.length - 1;
    let next: number | null = null;
    if (event.key === 'ArrowRight') next = index === last ? 0 : index + 1;
    else if (event.key === 'ArrowLeft') next = index === 0 ? last : index - 1;
    else if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = last;
    if (next === null) return;
    event.preventDefault();
    const target = tabs[next];
    onChange(target.id);
    const root = event.currentTarget.parentElement;
    root?.querySelectorAll<HTMLElement>('[role="tab"]')[next]?.focus();
  }

  return (
    <div className="argus-tabs" role="tablist" aria-label={ariaLabel}>
      {tabs.map((tab, index) => {
        const selected = tab.id === value;
        const common = {
          role: 'tab' as const,
          id: `tab-${tab.id}`,
          'aria-selected': selected,
          'aria-controls': `panel-${tab.id}`,
          tabIndex: selected ? 0 : -1,
          className: ['argus-tabs__tab', selected ? 'argus-tabs__tab--active' : ''].filter(Boolean).join(' '),
          onKeyDown: (event: KeyboardEvent<HTMLElement>) => onKeyDown(event, index),
        };
        if (tab.href) {
          return (
            <a
              key={tab.id}
              {...common}
              href={tab.href}
              onClick={(event: MouseEvent<HTMLAnchorElement>) => {
                if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
                event.preventDefault();
                onChange(tab.id);
              }}
            >
              {tab.label}
            </a>
          );
        }
        return (
          <button key={tab.id} type="button" {...common} onClick={() => onChange(tab.id)}>
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

interface TabPanelProps {
  id: string;
  active: boolean;
  children: ReactNode;
}

export function TabPanel({ id, active, children }: TabPanelProps) {
  if (!active) return null;
  return (
    <div role="tabpanel" id={`panel-${id}`} aria-labelledby={`tab-${id}`} className="argus-tabs__panel">
      {children}
    </div>
  );
}
