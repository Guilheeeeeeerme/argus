type LocaleValue = 'en' | 'pt-BR';

interface LocaleToggleProps {
  locale: string;
  label: string;
  ariaLabel: string;
  onLocaleChange: (next: LocaleValue) => void;
}

export function LocaleToggle({ locale, label, ariaLabel, onLocaleChange }: LocaleToggleProps) {
  const next: LocaleValue = locale === 'en' ? 'pt-BR' : 'en';
  return (
    <button
      type="button"
      className="argus-btn argus-btn--ghost argus-btn--sm"
      onClick={() => onLocaleChange(next)}
      aria-label={ariaLabel}
    >
      {label}
    </button>
  );
}
