import { apiFetch, isAllowedReturn, MAIN_ORIGIN, getToken } from '@shared/auth';
import type {
  AccountKind,
  AdminUser,
  Camera,
  Account,
  Unit,
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
  if (!isAllowedReturn(target)) return APP;
  return stripTokenHash(target);
}

/** Strip a prior `#token=` (and any other hash) so handoff never double-embeds. */
export function stripTokenHash(target: string): string {
  const hashIndex = target.indexOf('#');
  return hashIndex === -1 ? target : target.slice(0, hashIndex);
}

/** Append the session token as a hash so the destination app can adopt it. */
export function withToken(target: string): string {
  const token = getToken();
  const base = stripTokenHash(target);
  if (!token) return base;
  return `${base}#token=${encodeURIComponent(token)}`;
}

export interface SwitchContextBody {
  accountId?: string | null;
  unitId?: string | null;
}

export const auth = {
  me: () => apiFetch<Session>('/v1/auth/me'),
  login: (email: string, password: string) =>
    apiFetch<Session>('/v1/auth/login', json('POST', { email, password })),
  logout: () => apiFetch<unknown>('/v1/auth/logout', { method: 'POST' }),
  accounts: () => apiFetch<Account[]>('/v1/auth/accounts'),
  switchContext: (body: SwitchContextBody) =>
    apiFetch<Session>('/v1/auth/context', json('PATCH', body)),
};

export interface UnitInput {
  name: string;
  address: string | null;
  timezone: string;
  active?: boolean;
}

export const units = {
  list: (accountId: string) =>
    apiFetch<Unit[]>(`/v1/accounts/${accountId}/units`),
  get: (accountId: string, id: string) =>
    apiFetch<Unit>(`/v1/accounts/${accountId}/units/${id}`),
  create: (accountId: string, body: UnitInput) =>
    apiFetch<Unit>(`/v1/accounts/${accountId}/units`, json('POST', body)),
  update: (accountId: string, id: string, body: Partial<UnitInput>) =>
    apiFetch<Unit>(`/v1/accounts/${accountId}/units/${id}`, json('PATCH', body)),
  remove: (accountId: string, id: string) =>
    apiFetch<null>(`/v1/accounts/${accountId}/units/${id}`, DELETE),
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
  listAll: (accountId: string) => apiFetch<Camera[]>(`/v1/accounts/${accountId}/cameras`),
  list: (accountId: string, unitId: string, includeInactive = false) =>
    apiFetch<Camera[]>(
      `/v1/accounts/${accountId}/units/${unitId}/cameras${includeInactive ? '?include_inactive=true' : ''}`,
    ),
  create: (accountId: string, unitId: string, body: CameraInput) =>
    apiFetch<Camera>(`/v1/accounts/${accountId}/units/${unitId}/cameras`, json('POST', body)),
  update: (accountId: string, id: string, body: Partial<CameraInput>) =>
    apiFetch<Camera>(`/v1/accounts/${accountId}/cameras/${id}`, json('PATCH', body)),
  remove: (accountId: string, id: string) =>
    apiFetch<null>(`/v1/accounts/${accountId}/cameras/${id}`, DELETE),
};

export const promptSets = {
  list: (accountId: string, cameraId: string) =>
    apiFetch<PromptSet[]>(`/v1/accounts/${accountId}/cameras/${cameraId}/prompt-sets`),
  create: (accountId: string, cameraId: string, name: string) =>
    apiFetch<PromptSet>(`/v1/accounts/${accountId}/cameras/${cameraId}/prompt-sets`, json('POST', { name, prompts: [] })),
  rename: (accountId: string, id: string, name: string) =>
    apiFetch<PromptSet>(`/v1/accounts/${accountId}/prompt-sets/${id}`, json('PATCH', { name })),
  remove: (accountId: string, id: string) =>
    apiFetch<null>(`/v1/accounts/${accountId}/prompt-sets/${id}`, DELETE),
};

export interface PromptInput {
  text: string;
  enabled: boolean;
  sort_order?: number;
}

export const prompts = {
  create: (accountId: string, promptSetId: string, body: PromptInput) =>
    apiFetch<Prompt>(`/v1/accounts/${accountId}/prompt-sets/${promptSetId}/prompts`, json('POST', body)),
  update: (accountId: string, id: string, body: Partial<PromptInput>) =>
    apiFetch<Prompt>(`/v1/accounts/${accountId}/prompts/${id}`, json('PATCH', body)),
  remove: (accountId: string, id: string) =>
    apiFetch<null>(`/v1/accounts/${accountId}/prompts/${id}`, DELETE),
};

export interface WebhookInput {
  name: string;
  unit_id: string | null;
  active?: boolean;
}

export const webhooks = {
  list: (accountId: string) =>
    apiFetch<WebhookEndpoint[]>(`/v1/accounts/${accountId}/webhook-endpoints`),
  create: (accountId: string, body: WebhookInput) =>
    apiFetch<WebhookEndpoint>(`/v1/accounts/${accountId}/webhook-endpoints`, json('POST', body)),
  update: (accountId: string, id: string, body: Partial<WebhookInput>) =>
    apiFetch<WebhookEndpoint>(`/v1/accounts/${accountId}/webhook-endpoints/${id}`, json('PATCH', body)),
  rotate: (accountId: string, id: string) =>
    apiFetch<WebhookEndpoint>(`/v1/accounts/${accountId}/webhook-endpoints/${id}/rotate`, { method: 'POST' }),
  remove: (accountId: string, id: string) =>
    apiFetch<null>(`/v1/accounts/${accountId}/webhook-endpoints/${id}`, DELETE),
};

export interface UserInput {
  email: string;
  role: string;
  password?: string;
  account_ids: string[];
}

export const users = {
  list: () => apiFetch<AdminUser[]>('/v1/admin/users'),
  create: (body: UserInput) => apiFetch<AdminUser>('/v1/admin/users', json('POST', body)),
  update: (id: string, body: Partial<UserInput>) =>
    apiFetch<AdminUser>(`/v1/admin/users/${id}`, json('PATCH', body)),
  remove: (id: string) => apiFetch<null>(`/v1/admin/users/${id}`, DELETE),
};

export interface AccountInput {
  name: string;
  slug: string;
  kind: AccountKind;
}

export const accounts = {
  list: () => apiFetch<Account[]>('/v1/admin/accounts'),
  create: (body: AccountInput) => apiFetch<Account>('/v1/admin/accounts', json('POST', body)),
  update: (id: string, body: Partial<AccountInput>) =>
    apiFetch<Account>(`/v1/admin/accounts/${id}`, json('PATCH', body)),
  remove: (id: string) => apiFetch<null>(`/v1/admin/accounts/${id}`, DELETE),
};
