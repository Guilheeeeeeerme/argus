/**
 * Pure state for the triage case rail (docs/realtime-page.md).
 *
 * FOLLOW: focus tracks the newest open case; every `detection.created` switches to it.
 * PINNED: the operator chose a row (or closed the drawer); new cases only count in `newCount`.
 * `idle` returns to FOLLOW after VITE_TRIAGE_IDLE_MS without interaction.
 */
import type { TriageCase } from './api';

export type FocusMode = 'FOLLOW' | 'PINNED';

export interface FeedState {
  cases: TriageCase[];
  focusId: string | null;
  mode: FocusMode;
  newCount: number;
}

export type FeedAction =
  | { type: 'loaded'; cases: TriageCase[] }
  | { type: 'detection_created'; case: TriageCase }
  | { type: 'triage_updated'; id: string; patch: Partial<Pick<TriageCase, 'state' | 'resolved_at' | 'updated_at'>> }
  | { type: 'pin'; id: string }
  | { type: 'clear_focus' }
  | { type: 'idle' };

export const FEED_CAPACITY = 50;

export function initialFeedState(): FeedState {
  return { cases: [], focusId: null, mode: 'FOLLOW', newCount: 0 };
}

export function caseTimestamp(item: TriageCase): number {
  const raw = item.detection?.created_at ?? item.updated_at;
  const value = raw ? Date.parse(raw) : NaN;
  return Number.isNaN(value) ? 0 : value;
}

function sortNewestFirst(cases: TriageCase[]): TriageCase[] {
  return [...cases].sort((a, b) => caseTimestamp(b) - caseTimestamp(a));
}

/** Newest open case, else the newest case overall, else null. */
export function newestOpen(cases: TriageCase[]): TriageCase | null {
  return cases.find(item => item.state === 'open') ?? cases[0] ?? null;
}

export function caseFeedReducer(state: FeedState, action: FeedAction): FeedState {
  switch (action.type) {
    case 'loaded': {
      const cases = sortNewestFirst(action.cases).slice(0, FEED_CAPACITY);
      if (state.mode === 'PINNED' && state.focusId && cases.some(c => c.id === state.focusId)) {
        return { ...state, cases };
      }
      return { ...state, cases, mode: 'FOLLOW', focusId: newestOpen(cases)?.id ?? null, newCount: 0 };
    }
    case 'detection_created': {
      const exists = state.cases.some(c => c.id === action.case.id);
      const rest = state.cases.filter(c => c.id !== action.case.id);
      const cases = [action.case, ...rest].slice(0, FEED_CAPACITY);
      if (state.mode === 'FOLLOW') {
        return { ...state, cases, focusId: action.case.id, newCount: 0 };
      }
      return { ...state, cases, newCount: exists ? state.newCount : state.newCount + 1 };
    }
    case 'triage_updated': {
      let touched = false;
      const cases = state.cases.map(item => {
        if (item.id !== action.id) return item;
        touched = true;
        return { ...item, ...action.patch };
      });
      if (!touched) return state;
      const focused = cases.find(c => c.id === state.focusId);
      if (state.mode === 'FOLLOW' && focused && focused.state !== 'open') {
        const next = cases.find(c => c.state === 'open');
        return { ...state, cases, focusId: next?.id ?? state.focusId };
      }
      return { ...state, cases };
    }
    case 'pin':
      return { ...state, mode: 'PINNED', focusId: action.id, newCount: 0 };
    case 'clear_focus':
      return { ...state, mode: 'PINNED', focusId: null };
    case 'idle':
      return { ...state, mode: 'FOLLOW', focusId: newestOpen(state.cases)?.id ?? null, newCount: 0 };
    default:
      return state;
  }
}

/** True when `capturedAt` is older than `ttlMs` (or unparseable / absent). */
export function isStale(capturedAt: string | null | undefined, now: number, ttlMs: number): boolean {
  if (!capturedAt) return true;
  const value = Date.parse(capturedAt);
  if (Number.isNaN(value)) return true;
  return now - value > ttlMs;
}

/** Exponential backoff with full jitter removed for determinism: 1 s, 2 s, 4 s … capped. */
export function backoffDelay(attempt: number, baseMs = 1000, maxMs = 30000): number {
  const exponent = Math.max(0, Math.min(attempt, 30));
  return Math.min(maxMs, baseMs * 2 ** exponent);
}

/** Open cases per camera, from the feed (live) — merged with the overview counts by the caller. */
export function openCountByCamera(cases: TriageCase[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const item of cases) {
    if (item.state !== 'open' || !item.detection) continue;
    counts.set(item.detection.camera_id, (counts.get(item.detection.camera_id) ?? 0) + 1);
  }
  return counts;
}
