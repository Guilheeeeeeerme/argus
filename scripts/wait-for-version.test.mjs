import test from 'node:test';
import assert from 'node:assert/strict';
import { waitForVersion } from './wait-for-version.mjs';

test('waits through stale releases and invalid responses for the expected service and sha', async () => {
  const replies = [new Error('unavailable'), { service: 'other', gitsha: 'new' }, { service: 'argus-api', gitsha: 'old' }, { service: 'argus-api', gitsha: 'new' }];
  const requests = [];
  await waitForVersion({ url: 'https://example.test', sha: 'new', timeoutMs: 1000, intervalMs: 1, log: () => {}, fetchImpl: async (url, options) => {
    requests.push({ url, options });
    const reply = replies.shift();
    if (reply instanceof Error) throw reply;
    return { ok: true, status: 200, json: async () => reply };
  } });
  assert.equal(requests.length, 4);
  assert.equal(requests[0].options.headers['Cache-Control'], 'no-cache');
  assert.ok(requests[0].options.signal);
  assert.ok(requests[0].url.includes('release=new'));
});

test('bounds a hung request by the overall deadline', async () => {
  const start = Date.now();
  await assert.rejects(waitForVersion({ url: 'https://example.test', sha: 'new', timeoutMs: 30, requestTimeoutMs: 500, intervalMs: 1, log: () => {}, fetchImpl: (_url, { signal }) => new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new Error('aborted')), { once: true })) }), /did not report release new/);
  assert.ok(Date.now() - start < 1000);
});

test('never accepts a matching sha from an HTTP error response', async () => {
  await assert.rejects(waitForVersion({ url: 'https://example.test', sha: 'new', timeoutMs: 20, intervalMs: 1, log: () => {}, fetchImpl: async () => ({ ok: false, status: 503, json: async () => ({ service: 'argus-api', gitsha: 'new' }) }) }), /HTTP 503/);
});
