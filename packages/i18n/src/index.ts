export {
  SUPPORTED_LOCALES,
  resolveLocale,
  translate,
  localizeApiError,
  triageStateLabel,
  roleLabel,
} from './dictionary';
export type {
  Locale,
  TranslationVars,
  TranslationKey,
  TFunction,
} from './dictionary';
export { I18nProvider, useLocale, useT } from './i18n';
