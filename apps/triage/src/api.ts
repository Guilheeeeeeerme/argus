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
  establishment: { id: string; name: string; address: string | null } | null;
};

export type PromptHit = {
  prompt_id?: string;
  name?: string;
  text?: string;
  confidence?: number;
};

export type DetectionSummary = {
  id: string;
  camera_id: string;
  establishment_id: string;
  summary: string | null;
  confidence: number | null;
  prompt_hits: PromptHit[];
  clip_uri: string | null;
  frame_uris?: string[] | null;
  created_at?: string | null;
};

export type TriageCase = {
  id: string;
  detection_id: string;
  state: 'open' | 'confirmed' | 'dismissed' | 'false_positive' | string;
  updated_at: string | null;
  resolved_at?: string | null;
  detection: DetectionSummary | null;
  clip_playback_url?: string | null;
};

export type SessionLookup =
  | { ok: true; session: Session }
  | { ok: true; companyless: true }
  | { ok: false };

export async function loadSession(): Promise<SessionLookup> {
  try {
    const me = (await apiFetch('/v1/auth/me')) as {
      user: { email: string; role: string };
      activeCompany: { id: string; name: string } | null;
      activeEstablishment: { id: string; name: string; address: string | null } | null;
    };
    if (!me.activeCompany) return { ok: true, companyless: true };
    return {
      ok: true,
      session: {
        company_id: me.activeCompany.id,
        company_name: me.activeCompany.name,
        role: me.user.role,
        email: me.user.email,
        establishment: me.activeEstablishment,
      },
    };
  } catch {
    return { ok: false };
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

export function confidencePercent(value: number | null | undefined): number | null {
  if (value == null) return null;
  return value <= 1 ? Math.round(value * 100) : Math.round(value);
}
