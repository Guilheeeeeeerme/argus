import {
  API as API_BASE,
  WS as WS_BASE,
  apiFetch,
  consumeTokenFromUrl,
  getToken,
  redirectToLogin,
  MAIN_ORIGIN,
} from '@shared/auth';

export const API = API_BASE;
export const WS = WS_BASE;
export { apiFetch, consumeTokenFromUrl, getToken, redirectToLogin };

/** Unidade in the UI; `establishment` identifiers stay until the Phase 3 rename. */
export type Unit = { id: string; name: string; address: string | null; timezone?: string };

export type Session = {
  company_id: string;
  company_name: string;
  role: string;
  email: string;
  establishment: Unit | null;
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
  camera_name?: string | null;
  establishment_name?: string | null;
  sequence_id?: string | null;
  summary: string | null;
  confidence: number | null;
  prompt_hits: PromptHit[];
  clip_uri: string | null;
  created_at?: string | null;
};

export type TriageState = 'open' | 'confirmed' | 'dismissed' | 'false_positive';

export type TriageCase = {
  id: string;
  detection_id: string;
  state: TriageState | string;
  updated_at: string | null;
  resolved_at?: string | null;
  detection: DetectionSummary | null;
};

export type TriageCaseDetail = TriageCase & { clip_playback_url?: string | null };

export type CameraOverview = {
  id: string;
  name: string;
  is_active: boolean;
  last_frame_at: string | null;
  open_case_count: number;
};

export type SessionLookup =
  | { ok: true; session: Session }
  | { ok: true; companyless: true }
  | { ok: false };

interface MeResponse {
  user: { email: string; role: string };
  activeCompany: { id: string; name: string } | null;
  activeEstablishment: Unit | null;
}

function toSession(me: MeResponse): SessionLookup {
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
}

export async function loadSession(): Promise<SessionLookup> {
  try {
    return toSession(await apiFetch<MeResponse>('/v1/auth/me'));
  } catch {
    return { ok: false };
  }
}

export function listUnits(companyId: string): Promise<Unit[]> {
  return apiFetch<Unit[]>(`/v1/companies/${companyId}/establishments`);
}

/** Switch the session's active Unidade; returns the refreshed session. */
export async function switchUnit(unitId: string | null): Promise<SessionLookup> {
  const me = await apiFetch<MeResponse>('/v1/auth/context', {
    method: 'PATCH',
    body: JSON.stringify({ establishmentId: unitId }),
  });
  return toSession(me);
}

export function cameraOverview(companyId: string, unitId: string): Promise<CameraOverview[]> {
  return apiFetch<CameraOverview[]>(
    `/v1/companies/${companyId}/establishments/${unitId}/cameras/overview`,
  );
}

export interface ListCasesOptions {
  establishmentId?: string;
  cameraId?: string;
  /** `null` lists every state (open + recent resolutions); default is the API's `open`. */
  state?: TriageState | null;
  limit?: number;
}

export function listCases(companyId: string, options: ListCasesOptions = {}): Promise<TriageCase[]> {
  const params = new URLSearchParams();
  if (options.establishmentId) params.set('establishment_id', options.establishmentId);
  if (options.cameraId) params.set('camera_id', options.cameraId);
  if (options.state === null) params.set('state', '');
  else if (options.state) params.set('state', options.state);
  if (options.limit) params.set('limit', String(options.limit));
  const query = params.toString();
  return apiFetch<TriageCase[]>(`/v1/companies/${companyId}/triage-cases${query ? `?${query}` : ''}`);
}

export function getCase(companyId: string, caseId: string): Promise<TriageCaseDetail> {
  return apiFetch<TriageCaseDetail>(`/v1/companies/${companyId}/triage-cases/${caseId}`);
}

export type Disposition = 'confirmed' | 'dismissed' | 'false_positive';

export interface ResolveResponse {
  triage_case_id: string;
  state: TriageState;
  resolved_at: string;
  resolved_by: string;
}

export function resolveCase(
  companyId: string,
  caseId: string,
  body: { disposition: Disposition; reasoning: string | null },
): Promise<ResolveResponse> {
  return apiFetch<ResolveResponse>(`/v1/companies/${companyId}/triage-cases/${caseId}/resolve`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  return fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'content-type': 'application/json',
      ...(token ? { authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
}

export type LatestFrameResult =
  | { status: 'ok'; blob: Blob; etag: string | null; capturedAt: string | null }
  | { status: 'not_modified' }
  | { status: 'missing' }
  | { status: 'error' };

/** Poll the newest JPEG of a camera. Sends `If-None-Match` so unchanged frames cost a 304. */
export async function fetchLatestFrame(
  companyId: string,
  cameraId: string,
  etag: string | null,
  signal?: AbortSignal,
): Promise<LatestFrameResult> {
  let response: Response;
  try {
    response = await authedFetch(`/v1/companies/${companyId}/cameras/${cameraId}/latest-frame`, {
      headers: etag ? { 'If-None-Match': etag } : {},
      signal,
    });
  } catch {
    return { status: 'error' };
  }
  if (response.status === 304) return { status: 'not_modified' };
  if (response.status === 404) return { status: 'missing' };
  if (response.status === 401) {
    redirectToLogin();
    return { status: 'error' };
  }
  if (!response.ok) return { status: 'error' };
  const blob = await response.blob();
  return {
    status: 'ok',
    blob,
    etag: response.headers.get('etag'),
    capturedAt: response.headers.get('x-captured-at'),
  };
}

export function confidencePercent(value: number | null | undefined): number | null {
  if (value == null) return null;
  return value <= 1 ? Math.round(value * 100) : Math.round(value);
}

export function selectCompany(): void {
  const target = new URL(MAIN_ORIGIN);
  target.searchParams.set('returnTo', window.location.origin + window.location.pathname);
  const token = getToken();
  if (token) target.hash = `token=${encodeURIComponent(token)}`;
  window.location.assign(target.toString());
}
