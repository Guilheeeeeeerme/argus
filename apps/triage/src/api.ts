import {
  API as API_BASE,
  WS as WS_BASE,
  apiFetch,
  consumeTokenFromUrl,
  getToken,
  redirectToLogin,
} from '@shared/auth';

export const API = API_BASE;
export const WS = WS_BASE;
export { apiFetch, consumeTokenFromUrl, getToken, redirectToLogin };

export type Session = {
  company_id: string;
  company_name: string;
  role: string;
  email: string;
  location: { id: string; name: string; address: string | null } | null;
};

export async function loadSession(): Promise<Session | null> {
  try {
    const me = (await apiFetch('/v1/auth/me')) as {
      user: { email: string; role: string };
      activeCompany: { id: string; name: string } | null;
      activeLocation: { id: string; name: string; address: string | null } | null;
    };
    if (!me.activeCompany) return null;
    return {
      company_id: me.activeCompany.id,
      company_name: me.activeCompany.name,
      role: me.user.role,
      email: me.user.email,
      location: me.activeLocation,
    };
  } catch {
    return null;
  }
}

export function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  return fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'content-type': 'application/json',
      ...(token ? { authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  });
}
