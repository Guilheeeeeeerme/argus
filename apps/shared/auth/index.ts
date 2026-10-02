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

export type FieldErrors = Record<string, string>;

/**
 * Typed API failure. `detail` is the server message: the API answers
 * `{error: {code, message, status, details?}}` (see `argus.core.exceptions`);
 * FastAPI's plain `{detail}` is accepted as a fallback. Validation `details`
 * (`[{loc, msg}]`) are flattened into `fieldErrors` keyed by the last `loc` segment.
 * `status` is 0 when the request never reached the server.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly fieldErrors: FieldErrors;

  constructor(status: number, detail: string, fieldErrors: FieldErrors = {}) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.fieldErrors = fieldErrors;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

interface ValidationItem {
  loc?: unknown;
  msg?: unknown;
}

async function toApiError(response: Response): Promise<ApiError> {
  const text = await response.text().catch(() => '');
  let detail = text || response.statusText || `HTTP ${response.status}`;
  const fieldErrors: FieldErrors = {};
  try {
    const body = JSON.parse(text) as {
      error?: { message?: unknown; details?: unknown };
      detail?: unknown;
    };
    const message = body.error?.message ?? body.detail;
    const items = body.error?.details ?? body.detail;
    if (Array.isArray(items)) {
      for (const item of items as ValidationItem[]) {
        const loc = Array.isArray(item.loc) ? item.loc : [];
        const field = loc.length ? String(loc[loc.length - 1]) : '';
        if (field && typeof item.msg === 'string' && !(field in fieldErrors)) {
          fieldErrors[field] = item.msg;
        }
      }
    }
    if (typeof message === 'string' && message) {
      detail = message;
    } else if (Object.keys(fieldErrors).length) {
      detail = Object.values(fieldErrors)[0];
    }
  } catch {
    /* non-JSON body: keep raw text */
  }
  return new ApiError(response.status, detail, fieldErrors);
}

export async function apiFetch<T = unknown>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        'content-type': 'application/json',
        ...(token ? { authorization: `Bearer ${token}` } : {}),
        ...(init.headers ?? {}),
      },
    });
  } catch (error) {
    throw new ApiError(0, error instanceof Error ? error.message : 'Network error');
  }
  if (response.status === 401 && !path.startsWith('/v1/auth/login')) {
    clearToken();
    redirectToLogin();
    throw new ApiError(401, 'Session expired');
  }
  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return null as T;
  return (await response.json()) as T;
}

export async function getSession(): Promise<Session> {
  return (await apiFetch('/v1/auth/me')) as Session;
}
