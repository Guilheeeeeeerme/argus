import { apiFetch, isAllowedReturn, MAIN_ORIGIN, getToken } from '@shared/auth';
import type {
  AdminUser,
  Camera,
  Company,
  Establishment,
  Prompt,
  PromptSet,
  Session,
  WebhookEndpoint,
} from './types';

export const APP = MAIN_ORIGIN;

function json(method: 'POST' | 'PATCH' | 'PUT', body: unknown): RequestInit {
  return { method, body: JSON.stringify(body) };
}

const DELETE: RequestInit = { method: 'DELETE' };

/** `?returnTo=` from the current URL when it points at an allowed origin, else the admin origin. */
export function returnTo(): string {
  const target = new URLSearchParams(window.location.search).get('returnTo');
  if (!target) return APP;
  return isAllowedReturn(target) ? target : APP;
}

/** Append the session token as a hash so the destination app can adopt it. */
export function withToken(target: string): string {
  const token = getToken();
  if (!token) return target;
  return `${target}#token=${encodeURIComponent(token)}`;
}

export interface SwitchContextBody {
  companyId?: string | null;
  establishmentId?: string | null;
}

export const auth = {
  me: () => apiFetch<Session>('/v1/auth/me'),
  login: (email: string, password: string) =>
    apiFetch<Session>('/v1/auth/login', json('POST', { email, password })),
  logout: () => apiFetch<unknown>('/v1/auth/logout', { method: 'POST' }),
  companies: () => apiFetch<Company[]>('/v1/auth/companies'),
  switchContext: (body: SwitchContextBody) =>
    apiFetch<Session>('/v1/auth/context', json('PATCH', body)),
};

export interface EstablishmentInput {
  name: string;
  address: string | null;
  timezone: string;
  active?: boolean;
}

export const units = {
  list: (companyId: string) =>
    apiFetch<Establishment[]>(`/v1/companies/${companyId}/establishments`),
  get: (companyId: string, id: string) =>
    apiFetch<Establishment>(`/v1/companies/${companyId}/establishments/${id}`),
  create: (companyId: string, body: EstablishmentInput) =>
    apiFetch<Establishment>(`/v1/companies/${companyId}/establishments`, json('POST', body)),
  update: (companyId: string, id: string, body: Partial<EstablishmentInput>) =>
    apiFetch<Establishment>(`/v1/companies/${companyId}/establishments/${id}`, json('PATCH', body)),
  remove: (companyId: string, id: string) =>
    apiFetch<null>(`/v1/companies/${companyId}/establishments/${id}`, DELETE),
};

export interface CameraInput {
  name: string;
  stream_url: string | null;
  stream_username?: string | null;
  stream_password?: string | null;
  is_active?: boolean;
}

export const cameras = {
  /** Every active camera of the Conta, across units. */
  listAll: (companyId: string) => apiFetch<Camera[]>(`/v1/companies/${companyId}/cameras`),
  list: (companyId: string, unitId: string, includeInactive = false) =>
    apiFetch<Camera[]>(
      `/v1/companies/${companyId}/establishments/${unitId}/cameras${includeInactive ? '?include_inactive=true' : ''}`,
    ),
  create: (companyId: string, unitId: string, body: CameraInput) =>
    apiFetch<Camera>(`/v1/companies/${companyId}/establishments/${unitId}/cameras`, json('POST', body)),
  update: (companyId: string, id: string, body: Partial<CameraInput>) =>
    apiFetch<Camera>(`/v1/companies/${companyId}/cameras/${id}`, json('PATCH', body)),
  remove: (companyId: string, id: string) =>
    apiFetch<null>(`/v1/companies/${companyId}/cameras/${id}`, DELETE),
};

export const promptSets = {
  list: (companyId: string, cameraId: string) =>
    apiFetch<PromptSet[]>(`/v1/companies/${companyId}/cameras/${cameraId}/prompt-sets`),
  create: (companyId: string, cameraId: string, name: string) =>
    apiFetch<PromptSet>(`/v1/companies/${companyId}/cameras/${cameraId}/prompt-sets`, json('POST', { name, prompts: [] })),
  rename: (companyId: string, id: string, name: string) =>
    apiFetch<PromptSet>(`/v1/companies/${companyId}/prompt-sets/${id}`, json('PATCH', { name })),
  remove: (companyId: string, id: string) =>
    apiFetch<null>(`/v1/companies/${companyId}/prompt-sets/${id}`, DELETE),
};

export interface PromptInput {
  text: string;
  enabled: boolean;
  sort_order?: number;
}

export const prompts = {
  create: (companyId: string, promptSetId: string, body: PromptInput) =>
    apiFetch<Prompt>(`/v1/companies/${companyId}/prompt-sets/${promptSetId}/prompts`, json('POST', body)),
  update: (companyId: string, id: string, body: Partial<PromptInput>) =>
    apiFetch<Prompt>(`/v1/companies/${companyId}/prompts/${id}`, json('PATCH', body)),
  remove: (companyId: string, id: string) =>
    apiFetch<null>(`/v1/companies/${companyId}/prompts/${id}`, DELETE),
};

export interface WebhookInput {
  name: string;
  establishment_id: string | null;
  active?: boolean;
}

export const webhooks = {
  list: (companyId: string) =>
    apiFetch<WebhookEndpoint[]>(`/v1/companies/${companyId}/webhook-endpoints`),
  create: (companyId: string, body: WebhookInput) =>
    apiFetch<WebhookEndpoint>(`/v1/companies/${companyId}/webhook-endpoints`, json('POST', body)),
  update: (companyId: string, id: string, body: Partial<WebhookInput>) =>
    apiFetch<WebhookEndpoint>(`/v1/companies/${companyId}/webhook-endpoints/${id}`, json('PATCH', body)),
  rotate: (companyId: string, id: string) =>
    apiFetch<WebhookEndpoint>(`/v1/companies/${companyId}/webhook-endpoints/${id}/rotate`, { method: 'POST' }),
  remove: (companyId: string, id: string) =>
    apiFetch<null>(`/v1/companies/${companyId}/webhook-endpoints/${id}`, DELETE),
};

export interface UserInput {
  email: string;
  role: string;
  password?: string;
  company_ids: string[];
}

export const users = {
  list: () => apiFetch<AdminUser[]>('/v1/admin/users'),
  create: (body: UserInput) => apiFetch<AdminUser>('/v1/admin/users', json('POST', body)),
  update: (id: string, body: Partial<UserInput>) =>
    apiFetch<AdminUser>(`/v1/admin/users/${id}`, json('PATCH', body)),
  remove: (id: string) => apiFetch<null>(`/v1/admin/users/${id}`, DELETE),
};

export interface CompanyInput {
  name: string;
  slug: string;
}

export const accounts = {
  list: () => apiFetch<Company[]>('/v1/admin/companies'),
  create: (body: CompanyInput) => apiFetch<Company>('/v1/admin/companies', json('POST', body)),
  update: (id: string, body: Partial<CompanyInput>) =>
    apiFetch<Company>(`/v1/admin/companies/${id}`, json('PATCH', body)),
  remove: (id: string) => apiFetch<null>(`/v1/admin/companies/${id}`, DELETE),
};
