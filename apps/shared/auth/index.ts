export const API_BASE = (import.meta.env?.VITE_API_BASE as string | undefined) ?? '/api';
export const WS_BASE = (import.meta.env?.VITE_WS_BASE as string | undefined) ?? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;
export const MAIN_ORIGIN = (import.meta.env?.VITE_MAIN_ORIGIN as string | undefined) ?? 'http://localhost:8180';
export const TRIAGE_ORIGIN = (import.meta.env?.VITE_SUPPORT_ORIGIN as string | undefined) ?? 'http://localhost:8181';
export const API = API_BASE;
export const WS = WS_BASE;

const TOKEN_KEY = 'argus_token';

export interface User {
  id: string;
  email: string;
  role: string;
  companyId: string | null;
}

export interface CompanyRef {
  id: string;
  name: string;
  slug: string;
}

export interface EstablishmentRef {
  id: string;
  name: string;
  address: string | null;
}

export type TenantRef = CompanyRef;
/** @deprecated Use EstablishmentRef */
export type MarketRef = EstablishmentRef;
/** @deprecated Use EstablishmentRef */
export type LocationRef = EstablishmentRef;

export interface Session {
  token?: string;
  user: User;
  activeCompany: CompanyRef | null;
  activeEstablishment: EstablishmentRef | null;
}

/** Session field helper — id of the active establishment, if any. */
export function activeEstablishmentId(session: Session): string | null {
  return session.activeEstablishment?.id ?? null;
}

export function allowedReturnOrigins(): string[] {
  const env = (import.meta.env?.VITE_SSO_RETURN_ORIGINS as string | undefined) ?? '';
  const list = env.split(',').map(s => s.trim()).filter(Boolean);
  return list.length > 0 ? list : [MAIN_ORIGIN, TRIAGE_ORIGIN];
}

export function isAllowedReturn(raw: string): boolean {
  try {
    const url = new URL(raw);
    return allowedReturnOrigins().includes(url.origin);
  } catch {
    return false;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function consumeTokenFromUrl(): string | null {
  const hash = window.location.hash;
  if (!hash.startsWith('#token=')) return getToken();
  const token = decodeURIComponent(hash.slice('#token='.length));
  setToken(token);
  history.replaceState(null, '', window.location.pathname + window.location.search);
  return token;
}

export function redirectToLogin(returnUrl: string = window.location.href): void {
  const target = isAllowedReturn(returnUrl) ? returnUrl : MAIN_ORIGIN;
  window.location.assign(`${MAIN_ORIGIN}/sso/handoff?returnUrl=${encodeURIComponent(target)}`);
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<unknown> {
  const token = getToken();
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'content-type': 'application/json',
      ...(token ? { authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  });
  if (response.status === 401 && !path.startsWith('/v1/auth/login')) {
    clearToken();
    redirectToLogin();
    throw new Error('Session expired');
  }
  if (!response.ok) throw new Error(await response.text());
  return response.status === 204 ? null : response.json();
}

export async function getSession(): Promise<Session> {
  return (await apiFetch('/v1/auth/me')) as Session;
}
