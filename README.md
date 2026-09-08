# Argus

Multi-company surveillance platform: an admin application (SSO host), a real-time triage micro-frontend, and an AI vision pipeline that turns camera streams into operator-ready decisions.

## Live

| Application | URL |
| --- | --- |
| Admin (SSO host) | https://app.argus.ferredemo.dev |
| Triage MFE | https://triage.argus.ferredemo.dev |
| API | https://api.argus.ferredemo.dev |
| Storage (signed URLs) | https://api.storage.argus.ferredemo.dev |

## Features

- **Postgres row-level security multi-tenancy** — every query is scoped at the database level through session context; company APIs read the tenant from the Redis session only, never from client-supplied claims.
- **SSO across micro-frontends** — opaque Redis-backed sessions with hash-token handoff and origin allow-listing; the triage MFE never shows a company switcher and inherits platform-user context switches on refresh.
- **Roles** — `root`/`admin` (platform, can switch company/location), `manager` and `operator` (single company).
- **Physical model** — locations with addresses and floor-plan sketches, edge agents bound N:N, cameras with RTSP stream configuration and placements.
- **AI analysis pipeline** — Celery workers run VLM detection over extracted frames against rule sets with shifts, recipes and detection bindings; decisions follow a state machine with alarms.
- **Real-time triage** — WebSocket event rail authenticated with session tokens.
- **S3-compatible storage** — private MinIO bucket with signed download URLs.
- **Edge M2M auth** — agent devices authenticate with client-credentials JWTs, decoupled from user sessions.

## Architecture

```
Admin (Vite)      = SSO login host + admin shell + company/location switcher
Triage MFE (Vite) = operator workspace (WS live updates)
Worker            = Celery on Redis — VLM analysis, aggregation, notifier, scheduler

Browser / MFE
    │  Authorization: Bearer <opaque-session-token>
    ▼
FastAPI API
    ├── Redis     → sessions + Celery broker + pub/sub (WS events)
    ├── Postgres  → companies, users, locations, cameras, decisions (pgvector) — RLS scoped
    └── MinIO     → frame/object storage with signed URLs
         ▼
    Celery worker → VLM analysis → decisions → notifications
```

## Tech stack

| Layer | Technology |
| --- | --- |
| API | Python 3.12, FastAPI, SQLAlchemy (async), Alembic |
| Database | PostgreSQL 16 with RLS + pgvector |
| Async | Celery, Redis (broker, sessions, pub/sub) |
| Storage | MinIO (S3 API, boto3) with signed URLs |
| Frontends | React, Vite, shared `@argus/design-system` package |
| Auth | Opaque Redis sessions, PyJWT client-credentials for edge devices |

## Guardrails & LLM spend

All LLM calls follow the Promptdesk guardrails standard (`apps/api/docs/guardrails.md`).

| OWASP risk (2026) | Mitigation |
| --- | --- |
| LLM01 Prompt injection | Untrusted feedback is screened at write and before LLM; remaining content is fenced in the user message. |
| LLM02 Sensitive disclosure | Keys never in prompts. Frames/prompts leave to Gemini/OpenAI by design — require DPA; prompt rules are defense-in-depth only. |
| LLM03 Excessive agency | No tools; WARNING notify requires triage HITL approve; severity uses allowlisted JSON + confidence floor. |
| LLM06 Unbounded consumption | Per-tenant + global Redis call budgets; optional token/cost halt; API per-IP rate limit. |

Providers and models:

- `LLM_PROVIDER_ORDER` (default `gemini,openai`): Gemini first, OpenAI optional fallback; providers without a key are skipped; `OPENAI_BASE_URL` is honored.
- Cheapest-first model rank (`integrations/model_rank.py`, Redis-cached, refreshed by the `models.refresh_rank` beat task every `MODEL_RANK_REFRESH_MS`, default 12h = twice daily): retries escalate through `rank[attempt]`, cross-provider failover only after all attempts of the earlier provider fail.
- VLM analysis is ingest-driven, not scheduled; embeddings remain OpenAI-only (`text-embedding-3-small`) with a deterministic local fallback.

## Local development

```bash
cp .env.example .env
./scripts/up.sh -d
```

Hot reload is automatic for the API (uvicorn) and frontends (Vite); restart the worker after Celery changes. No `/etc/hosts` entries are required.

| Service | URL |
| --- | --- |
| Admin (SSO host) | http://localhost:8180 |
| Triage MFE | http://localhost:8181 |
| API | http://localhost:8800 (`/health`, `/health/db`) |

Seeded data (2 companies with locations, agents, cameras and rule sets) is idempotent and runs on API start; seed credentials are listed in the seed output. Wipe with `docker compose down -v`.

## Repository layout

```
apps/api          FastAPI + Celery + Alembic (RLS multi-tenancy)
apps/admin        Admin app / SSO host + switcher
apps/triage       Triage operator MFE
apps/shared       Shared token + SSO helpers
packages/ui       @argus/design-system (tokens, theme, components)
docs/services     Service specs (stream-to-image, decision engine, notifications)
```

## Deployment

Production images, DNS, TLS and rollout are owned by a separate private infrastructure repository. Pushes to `main` request a deployment from that repository, which builds reproducible release bundles (application SHA + infrastructure SHA) and rolls them out with health-checked Compose deployments. Production boots without development fixtures: a bootstrap job creates the platform root account and provisions the storage bucket.
