import {
  apiFetch,
  isAllowedReturn,
  MAIN_ORIGIN,
  API_BASE,
  Session as AuthSession,
  User,
  TenantRef,
  EstablishmentRef,
  MarketRef,
} from '@shared/auth';

export const API = API_BASE;
export const APP = MAIN_ORIGIN;
export { isAllowedReturn, MAIN_ORIGIN as APP_ORIGIN };
export type { AuthSession, User, TenantRef, EstablishmentRef, MarketRef };

export type Session = AuthSession;
export type Company = { id: string; name: string; slug: string };
export type Establishment = {
  id: string;
  name: string;
  address: string | null;
  timezone: string;
  active?: boolean;
};
export type Camera = {
  id: string;
  establishment_id: string;
  name: string;
  stream_url: string | null;
  stream_username?: string | null;
  is_active: boolean;
};
export type Prompt = {
  id: string;
  prompt_set_id: string;
  text: string;
  enabled: boolean;
  sort_order: number;
};
export type PromptSet = {
  id: string;
  camera_id: string;
  name: string;
  prompts?: Prompt[];
};
export type WebhookEndpoint = {
  id: string;
  name: string;
  establishment_id: string | null;
  active?: boolean;
  token?: string;
};
export type Account = {
  id: string;
  company_id: string | null;
  email: string;
  idp_subject: string | null;
  role: string;
};

export const call = apiFetch as (path: string, init?: RequestInit) => Promise<unknown>;

export function returnTo(): string {
  const target = new URLSearchParams(window.location.search).get('returnTo');
  if (!target) return APP;
  return isAllowedReturn(target) ? target : APP;
}

export async function switchContext(body: {
  companyId?: string | null;
  establishmentId?: string | null;
}): Promise<Session> {
  return (await call('/v1/auth/context', { method: 'PATCH', body: JSON.stringify(body) })) as Session;
}
