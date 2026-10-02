import type { Session as AuthSession, User } from '@shared/auth';

export type Session = AuthSession;
export type { User };

/** Conta (account) in the UI; code identifiers stay `account` until the Phase 3 rename. */
export type AccountKind = 'company' | 'ngo' | 'school' | 'university' | 'other';

export const ACCOUNT_KINDS: ReadonlyArray<AccountKind> = ['company', 'ngo', 'school', 'university', 'other'];

export interface Account {
  id: string;
  name: string;
  slug: string;
  kind: AccountKind;
  aggregation_window_secs?: number;
}

/** Unidade (unit) in the UI; code identifiers stay `unit` until the Phase 3 rename. */
export interface Unit {
  id: string;
  name: string;
  address: string | null;
  timezone: string;
  active: boolean;
}

export interface Camera {
  id: string;
  unit_id: string;
  name: string;
  stream_url: string | null;
  stream_username: string | null;
  is_active: boolean;
}

export interface Prompt {
  id: string;
  prompt_set_id: string;
  text: string;
  enabled: boolean;
  sort_order: number;
}

export interface PromptSet {
  id: string;
  camera_id: string;
  name: string;
  prompts: Prompt[];
}

export interface WebhookEndpoint {
  id: string;
  name: string;
  unit_id: string | null;
  active: boolean;
  /** Raw token, present only on create and rotate responses. */
  token?: string | null;
}

export interface AdminUser {
  id: string;
  email: string;
  role: string;
  account_id: string | null;
  account_ids: string[];
  idp_subject: string | null;
}

export type UserRole = 'root' | 'admin' | 'manager' | 'operator';

export const PLATFORM_ROLES: ReadonlyArray<string> = ['root', 'admin'];

export function isPlatformRole(role: string): boolean {
  return PLATFORM_ROLES.includes(role);
}
