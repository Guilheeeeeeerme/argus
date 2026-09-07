# ARGUS

Multi-company surveillance platform - admin (SSO host) + triage MFE sharing Redis-backed opaque sessions, single Docker network (`argus_dmz`), hot reload everywhere. Development only: no TLS, plain HTTP.

## Architecture

```
Admin (:8180)     = SSO login host + admin shell + company/location switcher (root/admin)
Triage MFE (:8181)= operator workspace (WS live updates)
API (:8800)       = FastAPI — auth, admin, triage, ingest; RLS multi-tenancy
Worker            = Celery on Redis (VLM analyze, aggregation, notifier, scheduler)

Browser / MFE
    │  Authorization: Bearer <opaque-session-token>
    ▼
FastAPI (:8800, argus_dmz)
    ├── Redis     → sessions + Celery broker + pub/sub (WS events)
    └── Postgres  → companies, users, locations, cameras, decisions (pgvector) — RLS scoped
```

All services join the `argus_dmz` network; edge ports are published for the host/browser.

## Stack

- **API**: Python 3.12, FastAPI, SQLAlchemy async + Alembic, Postgres RLS, Redis (sessions/broker/pubsub), Celery
- **Frontends**: React + Vite (dev servers with bind mounts), shared `@argus/design-system` (`packages/ui`), shared SSO helpers (`apps/shared/auth`)
- **Infra**: docker compose — pgvector/pg16, redis 7

## Quick start

```bash
cp .env.example .env
./scripts/up.sh -d
```

If your machine does not already resolve `admin.argus.test` and `triage.argus.test`, add them to your hosts file so the browser can reach the two frontends over HTTP.

Hot reload is automatic: `uvicorn --reload` for the API, Vite dev servers for admin/triage (source bind-mounted). Celery requires a manual `docker compose restart worker` after worker code changes.

| Service | URL |
|---------|-----|
| Admin (SSO host) | http://admin.argus.test:8180 |
| Triage MFE | http://triage.argus.test:8181 |
| API | http://api.argus.test:8800 (`/health`, `/health/db`) |
| Postgres | `postgres:5432` (`argus`/`argus`) |
| Redis | `redis:6379` |

Wipe dev data: `docker compose down -v`.

## SSO flow (different origins cannot share localStorage)

1. Triage opens without a fresh `#token=` → redirect to `http://admin.argus.test:8180/sso/handoff?returnUrl=<encoded triage URL>`
2. Admin has a session → redirect to `returnUrl#token=<opaque>`
3. Otherwise → login form, then the same hash handoff
4. Triage stores the token (strips the hash) and calls `GET /v1/auth/me`

`SSO_RETURN_ORIGINS` / `VITE_SSO_RETURN_ORIGINS` prevent open redirects.

## Roles

| Role | Scope | Can switch company/location? |
|------|-------|---------------------------|
| `root` | Platform (us) | Yes — creates companies + users |
| `admin` | Platform (customer + support) | Yes — creates companies + users |
| `manager` | One company | No |
| `operator` | One company | No (triage; can edit rules) |

Triage MFE never shows a switcher. Platform users switch company + location on the admin app; MFEs read the updated session on refresh. **Security rule:** company APIs must use the Redis session `activeCompanyId` only — never a client-supplied `companyId` body/claim.

### Locations, agents, cameras

Locations carry an **address** and a **sketch** (floor plan) where cameras are placed. **Agents** (edge devices) bind to locations N:N. Cameras store industry-standard stream config (RTSP), served to the media layer by the stream-gateway. The active location's address feeds the agent's ingest context.

## Seed credentials

Password for all seeded users: **`Password123!`**

| Email | Role | Company |
|-------|------|--------|
| `root@argus.local` | root | — |
| `admin@argus.local` | admin | — |
| `manager.downtown@argus.local` | manager | Downtown Retail |
| `operator.downtown@argus.local` | operator | Downtown Retail |
| `manager.airport@argus.local` | manager | Airport Retail |
| `operator.airport@argus.local` | operator | Airport Retail |

Seed runs automatically on API start (idempotent): 2 companies × locations (sketches) + agents (N:N) + cameras (stream config + placements), rule set with shifts, recipe, rule with detection binding, notification config.

## Auth API

```http
Authorization: Bearer <session-token>
```

| Method | Path | Notes |
|--------|------|-------|
| `POST` | `/v1/auth/login` | `{ email, password }` → `{ token, user, activeCompany, activeLocation }` |
| `POST` | `/v1/auth/logout` | Deletes the Redis session |
| `GET` | `/v1/auth/me` | Session bootstrap for every app |
| `PATCH` | `/v1/auth/context` | `{ companyId? , locationId? }` — root/admin only |
| `GET` | `/v1/admin/companies` | List companies (platform) |
| `GET` | `/v1/admin/users` | List users (platform) |
| `POST` | `/v1/admin/users` | Create user with password (platform) |
| `GET/POST/PATCH/DELETE` | `/v1/companies/{id}/locations` | Location CRUD incl. `address` + sketch upload |
| `GET` | `/v1/companies/{id}/decisions` | Triage feed |
| `WS` | `/v1/ws?token=` | Live updates, session-token auth |

Edge agent devices authenticate with M2M client-credentials JWTs (`AUTH0_USE_MOCK=true` issues local HS256 tokens via `GET /v1/dev/session/edge`).

## Repo layout

```
apps/api           FastAPI + Celery + Alembic (RLS multi-tenancy)
apps/admin         Admin app / SSO host + switcher (Vite, :8180)
apps/triage        Triage MFE (Vite, :8181)
apps/shared/auth   Shared token + SSO helpers
packages/ui        @argus/design-system (tokens, theme, components)
docker-compose.yml postgres + redis + api + worker + admin + triage (argus_dmz)
scripts/up.sh      dev up + wait for health
```

## Service sketches (docs-first, not implemented)

- `docs/services/stream-to-image.md` — streams → temporary frame images
- `docs/services/image-analysis.md` — detections over rules (implemented in the worker; extraction path)
- `docs/services/decision-engine.md` — decisions, state machine, alarms (implemented; extraction path)
- `docs/services/notifications.md` — alarm delivery (partial; handoff)
- `docs/realtime-page.md` — triage event rail UX spec
- `docs/sketch-editor-mfe.md` — standalone drawing MFE (embeddable)

## Adding another MFE

1. New Vite app (e.g. `:8182`)
2. Reuse `@shared/auth`: `consumeTokenFromUrl` → else `redirectToLogin(MAIN_ORIGIN)`
3. Bootstrap with `loadSession()` / `GET /v1/auth/me`
4. Add origin to `SSO_RETURN_ORIGINS` + `VITE_SSO_RETURN_ORIGINS`
5. Add compose service + expose port
