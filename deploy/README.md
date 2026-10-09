# Argus — production deployment (Dokploy)

Branch `production` + a green `deploy.yml` build is the deploy contract: CI pushes immutable images to GHCR tagged `<sha>` and a moving `:production` tag, boots a compose smoke on the runner, then calls the Dokploy deploy hook and polls `/version` for the released SHA. The VPS never builds.

Runtime database stays the **existing Supabase project** — never repoint the DB URLs anywhere else. Everything here assumes the Dokploy/Traefik platform stacks (documented in the infra repo): Traefik (`websecure`, `letsencrypt`, `security-headers@file` + `compress@file` middlewares), `dokploy-network`, Garage object store (`http://object-store:9000`), Headroom LLM proxy (`http://headroom:8787`), per-app Redis is **inside this stack** (password + `noeviction`).

## Files

| Path | Role |
| --- | --- |
| `compose.prod.yml` | Dokploy stack: `migrate` (one-shot), `redis`, `api`, `worker` (Celery) + profile `pipeline` (stream-gateway, stream-gateway-sync, stream-prep, edge-cv, prompt-eval) |
| `smoke.compose.yml` | Runner-only override: local Postgres (pgvector) + MinIO for the CI smoke. Never deploy this. |
| `smoke.env` | Non-secret placeholder env for compose interpolation in CI |
| `docker/*.Dockerfile` | api, prompt-eval, stream-prep, stream-gateway-sync, edge-cv (multi-stage, non-root, `GIT_SHA` baked). go2rtc uses the upstream `alexxit/go2rtc:1.9.14` image — no Dockerfile. SPAs deploy via Cloudflare Pages (`.github/workflows/pages.yml`) — no Dockerfile. |
| `migrate.sh` | One-shot: `alembic upgrade head` (ADMIN_DATABASE_URL) → `ensure_grants.py` → `bootstrap.py`; `SKIP_MIGRATIONS=1` bypasses |
| `ops/ensure_grants.py` | Idempotent re-application of the `argus_app` role grants from alembic migrations 008/011 |
| `ops/bootstrap.py` | Platform ROOT seed + frame-bucket ensure (ported from infra) |
| `probe/pipeline_health.py` | Read-only dependency probe used as the pipeline services' healthcheck (ported verbatim from infra) |
| `env.production.example` | Panel env template — names only |
| `tiers/` | Memory budgets per VPS tier (16 GB / 8 GB) |

## Panel steps (Dokploy)

1. **Create the stack**: Project → Compose → Source = Generic Git. Paste repo URL, branch **`production`**, attach the repo deploy key (read-only). Provider stack = Docker Compose.
2. **Paste environment** from `env.production.example`, filled. Key notes:
# `DATABASE_URL` / `ADMIN_DATABASE_URL` point at the **existing Supabase pooler**: host `aws-0-eu-west-1.pooler.supabase.com`, DB `postgres`, schema `argus`, ports `6543` (pooled, transaction mode) and `5432` (direct/session). Scheme stays `postgresql+asyncpg://` (config drives asyncpg from apps/api config); on transaction-mode poolers append `?statement_cache_size=0` (pgBouncer + asyncpg prepared-statement conflict).
   - Owner role `argus` (migrations) and runtime role `argus_app` (NOBYPASSRLS) are separate roles; `ensure_grants.py` keeps `argus_app` non-superuser/NOBYPASSRLS and re-grants schema `argus` DML. Never merge them into one connection.
   - `REDIS_PASSWORD` is required; compose renders `redis://:<pw>@redis:6379/1` (pipeline_health enforces DB `/1`).
   - S3 is Garage: `S3_ENDPOINT_URL=http://object-store:9000`, bucket `argus-frames`.
   - LLM: `LLM_USE_HEADROOM=true`, `GEMINI_MODEL=gemini-3.1-flash-lite` (verified production pin), `GEMINI_BASE_URL=http://headroom:8787`.
   - Tier: paste `tiers/16gb.env` (incl. `COMPOSE_PROFILES=pipeline`) or `tiers/8gb.env` on the small VPS.
3. **GHCR pull credential** — configure the private-registry credentials in Dokploy so the stack can pull the `ghcr.io/guilheeeeeeerme/argus/*` images.
4. **Deploy**: Dokploy runs `docker compose up -d --wait` — `migrate` (restart: "no") runs first, then `api` depends on `migrate service_completed_successfully` + healthy Redis. `worker` waits for the healthy `api`.
5. Domain `api.argus.ferredemo.dev` → Traefik labels on the `api` service (compose labels), DNS-only A record, certificate via the Let's Encrypt resolver.
6. Pages (`pages.yml`) deploys the SPAs when pushed to `main` — needs `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID` repo secrets and existing Pages projects `argus-app` / `argus-triage`.

## Operations

- **Rollback**: GitHub Actions → *Deploy (Dokploy)* → workflow_dispatch with `sha` = previous commit. `production` moves to that SHA, the webhook redeploys. **Migrations must NOT be rolled forward-then-back by CI**: set `SKIP_MIGRATIONS=1` temporarily in the Dokploy panel env *before* redeploying an older SHA (it re-evaluates at re-deploy), then remove it. The deploy hook cannot carry dynamic env.
- `migrate` runs `alembic upgrade head` (idempotent/no-op at head) on every stack recreation; `SKIP_MIGRATIONS=1` short-circuits it (grants/bootstrap still applied).
- Secrets are panel-only: none of `DATABASE_URL`, `REDIS_PASSWORD`, provider keys, streams token, etc. appear in this repo. `smoke.env` holds throwaway CI values only.

## Stream gateway config (volume plan)

`stream-gateway` (go2rtc) mounts `stream-gateway-config:/config:ro`; `stream-gateway-sync` mounts the same volume read-write at `/config/go2rtc.yaml`, polls `api:8000/v1/internal/stream-configs` (token `X-Stream-Gateway-Token`) and rewrites the streams section durable + PATCHes in-memory state. The repo seed (`services/stream-gateway/go2rtc.yaml`) documents the local-dev baseline; in production, sync owns the file, so no bind mount from the repo. The sync container runs as root in compose (deviation, because Docker inits named volumes as root; the image itself is non-root-capable).

All the go2rtc/RTSP/WebRTC listener ports are **private-only**: the old `1984/8554/8555` host bindings are gone; cameras/stream-prep reach the gateway over the internal network only.

## Smoke (must pass before any deploy) — also done by CI on the runner

1. `docker compose --env-file deploy/smoke.env -f deploy/compose.prod.yml config -q` — valid render.
2. Runner boots prod compose with the smoke override: `migrate` completes → `api` healthy → worker Celery ping.
3. `GET /version` returns `{"gitsha": "<sha>", "service": "argus-api"}` — public (rate-limit exempt), no DB. The SHA is **baked into the image** at build time; leave panel `GIT_SHA` unset and keep `IMAGE_TAG=production` as the pull tag only.
4. Login at `app.argus.ferredemo.dev` (mock Auth0), triage WebSocket live ≥5 min.
5. `POST/GET /internal` from outside → Traefik noop → 404 on the edge. Real internal endpoints live under `/v1/internal` and are token-gated in the app.
6. `/health/db` returns `database: true` → pooler reachable with `argus_app`.
7. Backup restore drill (Supabase has no backups — keep the weekly external dump).

## Memory budgets (limits are env-overridable in compose)

| Tier | Core (api+worker+redis) | pipeline profile |
| --- | --- | --- |
| 16 GB | ≤ 1700 MB (700+800+200) | ≤ 2560 MB (1536+512+256+128+128) |
| 8 GB | ≤ 1150 MB (500+500+150) | OFF |
