import {
  apiFetch,
  isAllowedReturn,
  MAIN_ORIGIN,
  API_BASE,
  Session as AuthSession,
  User,
  TenantRef,
  MarketRef,
} from '@shared/auth';

export const API = API_BASE;
export const APP = MAIN_ORIGIN;
export { isAllowedReturn, MAIN_ORIGIN as APP_ORIGIN };
export type { AuthSession, User, TenantRef, MarketRef };

export type Session = AuthSession;
export type Company = { id: string; name: string; slug: string };
export type Location = { id: string; name: string; address: string | null; sketch: string | null; timezone: string };
export type Camera = { id: string; location_id: string; name: string; stream_url: string | null; placement_x: number | null; placement_y: number | null; is_active: boolean };
export type Account = { id: string; company_id: string | null; email: string; idp_subject: string | null; role: string };
export type Rule = { id: string; rule_set_id: string; name: string; detection_class: string | null; confidence_threshold: number; severity_weight: number };

export const call = apiFetch as (path: string, init?: RequestInit) => Promise<unknown>;

export function returnTo(): string {
  const target = new URLSearchParams(window.location.search).get('returnTo');
  if (!target) return APP;
  return isAllowedReturn(target) ? target : APP;
}

export async function switchContext(body: { companyId?: string | null; locationId?: string | null }): Promise<Session> {
  return (await call('/v1/auth/context', { method: 'PATCH', body: JSON.stringify(body) })) as Session;
}
