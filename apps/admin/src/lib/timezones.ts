const FALLBACK = [
  'UTC',
  'America/Sao_Paulo',
  'America/Manaus',
  'America/Fortaleza',
  'America/Recife',
  'America/Belem',
  'America/Cuiaba',
  'America/Porto_Velho',
  'America/Rio_Branco',
  'America/Noronha',
  'America/New_York',
  'America/Chicago',
  'America/Los_Angeles',
  'Europe/Lisbon',
  'Europe/London',
  'Europe/Madrid',
];

interface IntlWithValues {
  supportedValuesOf?: (key: 'timeZone') => string[];
}

let cache: string[] | null = null;

/** IANA time zones from the runtime when available, else a curated list. Always includes `current`. */
export function timeZoneOptions(current?: string | null): { value: string; label: string }[] {
  if (!cache) {
    const intl = Intl as unknown as IntlWithValues;
    try {
      cache = intl.supportedValuesOf ? intl.supportedValuesOf('timeZone') : FALLBACK;
    } catch {
      cache = FALLBACK;
    }
    if (!cache.includes('UTC')) cache = ['UTC', ...cache];
  }
  const list = current && !cache.includes(current) ? [current, ...cache] : cache;
  return list.map(zone => ({ value: zone, label: zone.replace(/_/g, ' ') }));
}

export function defaultTimeZone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch {
    return 'UTC';
  }
}
