import { describe, expect, it } from 'vitest';
import type { TriageCase } from '../api';
import {
  FEED_CAPACITY,
  backoffDelay,
  caseFeedReducer,
  initialFeedState,
  isStale,
  newestOpen,
  openCountByCamera,
} from '../feed';

function makeCase(id: string, state = 'open', createdAt = '2026-10-02T12:00:00Z', cameraId = 'cam-a'): TriageCase {
  return {
    id,
    detection_id: `det-${id}`,
    state,
    updated_at: createdAt,
    detection: {
      id: `det-${id}`,
      camera_id: cameraId,
      unit_id: 'unit-1',
      summary: null,
      confidence: null,
      prompt_hits: [],
      clip_uri: null,
      created_at: createdAt,
    },
  };
}

describe('caseFeedReducer', () => {
  it('loaded sorts newest first and follows the newest open case', () => {
    const state = caseFeedReducer(initialFeedState(), {
      type: 'loaded',
      cases: [
        makeCase('old', 'open', '2026-10-02T11:00:00Z'),
        makeCase('resolved', 'confirmed', '2026-10-02T13:00:00Z'),
        makeCase('new', 'open', '2026-10-02T12:00:00Z'),
      ],
    });
    expect(state.cases.map(c => c.id)).toEqual(['resolved', 'new', 'old']);
    expect(state.mode).toBe('FOLLOW');
    expect(state.focusId).toBe('new');
    expect(state.newCount).toBe(0);
  });

  it('FOLLOW switches focus to every new detection', () => {
    let state = caseFeedReducer(initialFeedState(), { type: 'loaded', cases: [makeCase('a')] });
    state = caseFeedReducer(state, { type: 'detection_created', case: makeCase('b', 'open', '2026-10-02T12:01:00Z') });
    expect(state.focusId).toBe('b');
    expect(state.cases[0].id).toBe('b');
    expect(state.newCount).toBe(0);
  });

  it('PINNED keeps focus and counts new detections', () => {
    let state = caseFeedReducer(initialFeedState(), { type: 'loaded', cases: [makeCase('a'), makeCase('b')] });
    state = caseFeedReducer(state, { type: 'pin', id: 'b' });
    state = caseFeedReducer(state, { type: 'detection_created', case: makeCase('c') });
    state = caseFeedReducer(state, { type: 'detection_created', case: makeCase('d') });
    expect(state.mode).toBe('PINNED');
    expect(state.focusId).toBe('b');
    expect(state.newCount).toBe(2);
    // duplicate delivery (at-least-once stream) does not inflate the pill
    state = caseFeedReducer(state, { type: 'detection_created', case: makeCase('d') });
    expect(state.newCount).toBe(2);
    expect(state.cases.filter(c => c.id === 'd')).toHaveLength(1);
  });

  it('idle returns to FOLLOW on the newest open case and clears the pill', () => {
    let state = caseFeedReducer(initialFeedState(), { type: 'loaded', cases: [makeCase('a')] });
    state = caseFeedReducer(state, { type: 'pin', id: 'a' });
    state = caseFeedReducer(state, { type: 'detection_created', case: makeCase('b', 'open', '2026-10-02T12:05:00Z') });
    state = caseFeedReducer(state, { type: 'idle' });
    expect(state.mode).toBe('FOLLOW');
    expect(state.focusId).toBe('b');
    expect(state.newCount).toBe(0);
  });

  it('clear_focus closes the drawer without auto-reopening on the next detection', () => {
    let state = caseFeedReducer(initialFeedState(), { type: 'loaded', cases: [makeCase('a')] });
    state = caseFeedReducer(state, { type: 'clear_focus' });
    expect(state.focusId).toBeNull();
    state = caseFeedReducer(state, { type: 'detection_created', case: makeCase('b') });
    expect(state.focusId).toBeNull();
    expect(state.newCount).toBe(1);
  });

  it('triage_updated patches the row and moves FOLLOW focus to the next open case', () => {
    let state = caseFeedReducer(initialFeedState(), {
      type: 'loaded',
      cases: [makeCase('a', 'open', '2026-10-02T12:00:00Z'), makeCase('b', 'open', '2026-10-02T12:01:00Z')],
    });
    expect(state.focusId).toBe('b');
    state = caseFeedReducer(state, { type: 'triage_updated', id: 'b', patch: { state: 'confirmed', resolved_at: 'x' } });
    expect(state.cases.find(c => c.id === 'b')?.state).toBe('confirmed');
    expect(state.focusId).toBe('a');
    const same = caseFeedReducer(state, { type: 'triage_updated', id: 'nope', patch: { state: 'dismissed' } });
    expect(same).toBe(state);
  });

  it('caps the rail at FEED_CAPACITY rows', () => {
    const many = Array.from({ length: FEED_CAPACITY + 10 }, (_, i) =>
      makeCase(`c${i}`, 'open', `2026-10-02T12:${String(i % 60).padStart(2, '0')}:00Z`),
    );
    let state = caseFeedReducer(initialFeedState(), { type: 'loaded', cases: many });
    expect(state.cases).toHaveLength(FEED_CAPACITY);
    state = caseFeedReducer(state, { type: 'detection_created', case: makeCase('fresh') });
    expect(state.cases).toHaveLength(FEED_CAPACITY);
    expect(state.cases[0].id).toBe('fresh');
  });

  it('loaded keeps a PINNED focus that still exists', () => {
    let state = caseFeedReducer(initialFeedState(), { type: 'loaded', cases: [makeCase('a'), makeCase('b')] });
    state = caseFeedReducer(state, { type: 'pin', id: 'a' });
    state = caseFeedReducer(state, { type: 'loaded', cases: [makeCase('a'), makeCase('c')] });
    expect(state.mode).toBe('PINNED');
    expect(state.focusId).toBe('a');
    state = caseFeedReducer(state, { type: 'loaded', cases: [makeCase('c')] });
    expect(state.mode).toBe('FOLLOW');
    expect(state.focusId).toBe('c');
  });
});

describe('helpers', () => {
  it('newestOpen prefers open rows, else the first', () => {
    expect(newestOpen([])).toBeNull();
    expect(newestOpen([makeCase('x', 'dismissed'), makeCase('y', 'open')])?.id).toBe('y');
    expect(newestOpen([makeCase('x', 'dismissed')])?.id).toBe('x');
  });

  it('isStale honours the TTL and rejects bad input', () => {
    const now = Date.parse('2026-10-02T12:00:30Z');
    expect(isStale('2026-10-02T12:00:10Z', now, 30_000)).toBe(false);
    expect(isStale('2026-10-02T11:59:59Z', now, 30_000)).toBe(true);
    expect(isStale(null, now, 30_000)).toBe(true);
    expect(isStale('not a date', now, 30_000)).toBe(true);
  });

  it('backoffDelay doubles and caps', () => {
    expect([0, 1, 2, 3].map(a => backoffDelay(a))).toEqual([1000, 2000, 4000, 8000]);
    expect(backoffDelay(10)).toBe(30000);
    expect(backoffDelay(99, 500, 5000)).toBe(5000);
  });

  it('openCountByCamera counts only open rows', () => {
    const counts = openCountByCamera([
      makeCase('a', 'open', undefined, 'cam-1'),
      makeCase('b', 'open', undefined, 'cam-1'),
      makeCase('c', 'confirmed', undefined, 'cam-1'),
      makeCase('d', 'open', undefined, 'cam-2'),
    ]);
    expect(counts.get('cam-1')).toBe(2);
    expect(counts.get('cam-2')).toBe(1);
  });
});
