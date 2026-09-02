# Development HTTPS and hot reload

The development stack uses Vite containers with bind mounts and Caddy as the
local HTTPS gateway. Add these entries to `/etc/hosts`:

```text
127.0.0.1 app.development.argus.com triage.development.argus.com
127.0.0.1 api.development.argus.com ingest.development.argus.com ws.development.argus.com
```

Start the stack from the repository root:

```bash
docker compose up --build
```

This starts Core Admin only. Start platform services and MFEs when testing the
full pipeline:

```bash
docker compose --profile platform --profile mfe up --build
```

The browser URLs are:

- `https://app.development.argus.com` — Admin Dashboard
- `https://triage.development.argus.com` — Triage SPA

Direct Vite ports remain available at `http://localhost:3000` and
`http://localhost:3001` for troubleshooting. Source changes hot reload through
the bind mounts. Caddy creates a local CA for the `*.development.argus.com`
certificates; install the root certificate from:

```bash
docker compose -f backend/docker/docker-compose.yml cp dev-gateway:/data/caddy/pki/authorities/local/root.crt ./dev/caddy-root.crt
```

Trust `dev/caddy-root.crt` in the development browser/OS. Do not trust or copy
this certificate into production systems.

The local mock login writes the short-lived development token to the shared
`.development.argus.com` cookie domain, so logging in on either SPA makes the
same development session available to the other SPA. Set `AUTH0_USE_MOCK=false`
and configure the Auth0 variables in the root `.env` when testing the real SSO
provider.
