# Argus

Multi-company vision platform (MVP): an admin application (SSO host), a
near-realtime triage micro-frontend, and an AI pipeline that turns camera
streams into operator-ready **TriageCases**.

## Live

| Application | URL |
| --- | --- |
| Admin (SSO host) | https://app.argus.ferredemo.dev |
| Triage MFE | https://triage.argus.ferredemo.dev |
| API | https://api.argus.ferredemo.dev |
| Storage (signed URLs) | https://api.storage.argus.ferredemo.dev |

## Architecture (MVP)

```
stream-gateway (go2rtc)
        │
        ▼
   stream-prep          frames → MinIO (TTL) → Redis frames:ready
        │
        ▼
   prompt-eval          Gemini PromptSet eval; negatives discarded
        │               positives → Detection + clip + TriageCase
        │               Redis detections:positive
        ▼
   api                  CRUD, inbound webhooks, WS fan-out
        │
        ├── admin MFE   company / establishment / camera / PromptSet
        └── triage MFE  TriageCase HITL (open → confirmed|dismissed|false_positive)
```

| Piece | Role |
| --- | --- |
| **stream-prep** | Sample + preprocess frames from go2rtc; publish `frames:ready` |
| **prompt-eval** | Multimodal PromptSet evaluation; positive Detection + clip ≤ 10 min |
| **api** | CRUD, Bearer webhooks → `context:events`, WS `detection.created` / `triage.updated` |
| **admin** | SSO login host + admin shell + company/establishment switcher |
| **triage** | Operator workspace (near-realtime case rail) |

Supporting data plane: Postgres (RLS + pgvector), Redis (sessions, streams,
pub/sub), MinIO (ephemeral frames + evidence clips).

Product detail: [`docs/SPEC.md`](docs/SPEC.md). AI module map:
[`docs/ai-engineering.md`](docs/ai-engineering.md). Service handoffs:
[`docs/services/`](docs/services/).

## Features

- **Postgres RLS multi-tenancy** — queries scoped via session context; company
  APIs read the tenant from the Redis session, never from client-supplied claims.
- **SSO across MFEs** — opaque Redis sessions with hash-token handoff and origin
  allow-listing; triage inherits platform context switches on refresh.
- **Roles** — `root`/`admin` (platform, can switch company/establishment),
  `manager` and `operator` (single company).
- **Physical model** — establishments and cameras with RTSP config synced to
  stream-gateway.
- **PromptSet evaluation** — Gemini-first VLM over prepared frames; negatives
  discarded; positives open a TriageCase with evidence clip.
- **Context webhooks** — inbound Bearer-token endpoints publish `context:events`
  for grounding.
- **Near-realtime triage** — WebSocket `detection.created` / `triage.updated`.
- **S3-compatible storage** — private MinIO bucket with signed download URLs.

## Out of MVP scope

Agent edge devices, sketch/ROI editors, RuleSet/Recipe, SMS notifications, and
production Auth0. See `docs/SPEC.md` non-goals and
`docs/sketch-editor-mfe.md`.

## Tech stack

| Layer | Technology |
| --- | --- |
| API | Python 3.12, FastAPI, SQLAlchemy (async), Alembic |
| Pipeline | stream-prep, prompt-eval (Python services) |
| Database | PostgreSQL 16 with RLS + pgvector |
| Async | Redis (streams, sessions, pub/sub) |
| Storage | MinIO (S3 API) with signed URLs + frame TTL |
| Media | go2rtc stream-gateway |
| Frontends | React, Vite, shared `@argus/design-system` package |
| Auth | Opaque Redis sessions (Auth0 mock/scaffold only) |

## Guardrails & LLM spend

LLM calls follow the Promptdesk guardrails standard (`apps/api/docs/guardrails.md`).
Concept → module mapping: `docs/ai-engineering.md` (`guardrails`,
`provider_router`).

| OWASP risk (2026) | Mitigation |
| --- | --- |
| LLM01 Prompt injection | Untrusted feedback/webhook text screened; remaining content fenced in the user message. |
| LLM02 Sensitive disclosure | Keys never in prompts. Frames/prompts leave to Gemini/OpenAI by design — require DPA. |
| LLM03 Excessive agency | No tools; dispositions require triage HITL; structured JSON + confidence floor. |
| LLM06 Unbounded consumption | Per-tenant + global Redis call budgets; optional cost halt; API per-IP rate limit. |

Providers: `LLM_PROVIDER_ORDER` (default `gemini,openai`); Gemini first with
optional OpenAI fallback. Embeddings for RAG remain embedding-model based with
a deterministic local fallback when needed.

## Local development

This repository is development-oriented: `docker-compose.yml` runs a full local
stack with dedicated Postgres, Redis, and MinIO. Production does not use this
Compose file.

```bash
cp .env.example .env
./scripts/up.sh -d
```

Hot reload is automatic for the API (uvicorn) and frontends (Vite). No
`/etc/hosts` entries are required.

| Service | URL |
| --- | --- |
| Admin (SSO host) | http://localhost:8180 |
| Triage MFE | http://localhost:8181 |
| API | http://localhost:8800 (`/health`, `/health/db`) |

Seeded data is idempotent and runs on API start; wipe with
`docker compose down -v`.

## Repository layout

```
apps/api          FastAPI + Alembic (RLS multi-tenancy, webhooks, WS)
apps/admin        Admin app / SSO host + switcher
apps/triage       Triage operator MFE
apps/shared       Shared token + SSO helpers
packages/ui       @argus/design-system (tokens, theme, components)
docs/             SPEC, AI map, service handoffs, realtime triage UX
docs/services/    stream-prep, prompt-eval, api
```

## Deployment

Production images, shared data plane (Postgres/Redis/MinIO), DNS, TLS, and
rollout are owned by the private `infra` repository. This app only notifies
infra on push to `main` (`.github/workflows/infra.yml`) when repository
variable `INFRA_ENABLED=true` and secret `INFRA_DISPATCH_TOKEN` are set.
Infra builds reproducible release bundles and rolls them out with
health-checked Compose deployments. Redis DB index `/1` is a production
isolation detail on the shared Redis; local Compose keeps its own Redis on `/0`.
