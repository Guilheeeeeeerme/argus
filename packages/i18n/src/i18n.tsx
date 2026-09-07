import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  ReactNode,
} from 'react';
import {
  Locale,
  SUPPORTED_LOCALES,
  TranslationVars,
  TFunction,
  resolveLocale,
  translate,
} from './dictionary';

const STORAGE_KEY = 'argus.locale';

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
}

const I18nContext = createContext<I18nContextValue | null>(null);

function getInitialLocale(): Locale {
  if (typeof window === 'undefined') return 'en';
  const stored = localStorage.getItem(STORAGE_KEY);
  for (const locale of SUPPORTED_LOCALES) {
    if (stored === locale) return locale;
  }
  return resolveLocale(navigator.language);
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>(getInitialLocale);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, locale);
    } catch {
      /* storage may be blocked */
    }
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo(() => ({ locale, setLocale }), [locale]);
  return (
    <I18nContext.Provider value={value}>
      {children}
    </I18nContext.Provider>
  );
}

export function useLocale(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useLocale must be used within I18nProvider');
  return ctx;
}

export function useT(): TFunction {
  const { locale } = useLocale();
  return useMemo(
    () => (key: string, vars?: TranslationVars) => translate(locale, key, vars),
    [locale],
  );
}
