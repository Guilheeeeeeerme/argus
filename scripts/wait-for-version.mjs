import { pathToFileURL } from 'node:url';

export async function waitForVersion({ url, sha, timeoutMs = 900_000,
  requestTimeoutMs = 10_000, intervalMs = 15_000, fetchImpl = fetch,
  log = console.log }) {
  if (!url || !sha) throw new Error('API_PUBLIC_URL and RELEASE_SHA are required');
  const endpoint = new URL(`${url.replace(/\/$/, '')}/version`);
  endpoint.searchParams.set('release', sha);
  const deadline = Date.now() + timeoutMs;
  let last = 'no response';
  while (Date.now() < deadline) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), Math.min(requestTimeoutMs, deadline - Date.now()));
    try {
      endpoint.searchParams.set('probe', String(Date.now()));
      const response = await fetchImpl(endpoint.href, {
        signal: controller.signal, redirect: 'error',
        headers: { 'Cache-Control': 'no-cache', Pragma: 'no-cache' },
      });
      if (!response.ok) last = `HTTP ${response.status}`;
      else {
        const body = await response.json();
        // Log only the expected public identity fields, never arbitrary responses.
        last = `service=${String(body.service).slice(0, 80)} sha=${String(body.gitsha).slice(0, 80)}`;
        if (body.service === 'argus-api' && body.gitsha === sha) {
          log(`Confirmed argus-api release ${sha}`);
          return;
        }
      }
    } catch {
      last = controller.signal.aborted ? 'request timed out' : 'request failed or invalid JSON';
    } finally { clearTimeout(timer); }
    log(`Waiting for release ${sha}: ${last}`);
    const remaining = deadline - Date.now();
    if (remaining > 0) await new Promise(resolve => setTimeout(resolve, Math.min(intervalMs, remaining)));
  }
  throw new Error(`Public API did not report release ${sha} within ${timeoutMs}ms (${last}). Inspect Dokploy release state and public /version before retrying; deployment may still be running.`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  waitForVersion({ url: process.env.API_PUBLIC_URL, sha: process.env.RELEASE_SHA })
    .catch(error => { console.error(`::error::${error.message}`); process.exitCode = 1; });
}
