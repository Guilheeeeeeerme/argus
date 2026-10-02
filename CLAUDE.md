# CLAUDE.md — Argus

Multi-company vision platform (MVP): admin SSO host, near-realtime triage micro-frontend, and an AI pipeline that turns camera streams into operator-ready **TriageCases**.

Agent behavioral rules (including RTK): see [AGENTS.md](./AGENTS.md). UI: [STYLE_GUIDE.md](./STYLE_GUIDE.md). Guardrails: [docs/ai-engineering.md](./docs/ai-engineering.md), [apps/api/docs/guardrails.md](./apps/api/docs/guardrails.md).

## Live

| App | URL |
| --- | --- |
| Admin | https://app.argus.ferredemo.dev |
| Triage | https://triage.argus.ferredemo.dev |
| API | https://api.argus.ferredemo.dev |
| Storage | https://api.storage.argus.ferredemo.dev |

Production deploys are owned by the **infra** repo (GitHub Actions is the sole supported control plane — do not use Jenkins; VPS removal is CONFIRM-gated in infra after GHA is proven — `Deploy app` → GHCR → VPS). Production Postgres remains on the existing Supabase database (schema `argus`, runtime role `argus_app`). Alembic uses `ADMIN_DATABASE_URL`; migrations run before rollout through infra GitHub Actions. Local Compose uses its own Docker Postgres. Step-by-step: [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md).

## Layout

npm workspaces (`apps/*`, `apps/shared/*`, `packages/*`):

| Path | Role |
| --- | --- |
| `apps/api` | FastAPI (Python 3.12), SQLAlchemy async, Alembic, Celery |
| `apps/admin` | Vite/React admin + SSO host |
| `apps/triage` | Vite/React triage MFE |
| `apps/shared/auth` | Shared auth client helpers |
| `packages/ui` | `@argus/design-system` |
| `packages/i18n` | Shared i18n |
| `services/stream-gateway` | go2rtc |
| `services/stream-prep` | Frame sample → MinIO → Redis `frames:ready` |
| `services/prompt-eval` | Multimodal PromptSet eval → Detection / TriageCase |

Pipeline: `stream-gateway` → `stream-prep` → `prompt-eval` → `api` → admin / triage MFEs.

## Stack

- FE: React 19, Vite, Tailwind, oxlint
- BE: FastAPI, Postgres 16 + RLS + pgvector, Redis, MinIO
- LLM: Gemini / OpenAI (local Headroom via `GEMINI_BASE_URL` / `OPENAI_BASE_URL` in `.env.example`)

## Local

```bash
cp .env.example .env.local.docker   # Compose Postgres + bind-mount hot reload
cp .env.local.docker .env
./scripts/up.sh -d
```

**DB:** local = Compose Postgres (`.env.local.docker`); prod = existing Supabase Postgres, schema `argus`. Application hosting remains on the VPS.

Typical ports: admin `:8180`, triage `:8181`, API `:8800`. Redis DB `/0` locally vs `/1` in prod.

## Commands

```bash
# Frontend
npm run lint
npm run build

# API (from apps/api; needs Postgres + Redis for full suite)
PYTHONPATH=src pytest tests/
alembic upgrade head
```

CI pre-deploy subset (via infra `app_test.sh`): `tests/test_http_cors.py`, `tests/test_compose_contract.py`.

## Conventions

- Opaque Redis SSO + hash-token MFE handoff; tenant comes from the **session**, not client claims.
- UI only through `@argus/design-system` — see STYLE_GUIDE (no inline hex / ad-hoc CSS variables).
- Align LLM calls with the Promptdesk guardrails standard.
- MVP auth: mock Auth0 path (`AUTH0_USE_MOCK`); do not wire production Auth0 casually.
- Do not put API keys in prompts; do not log untrusted multimodal content beyond ids/statuses.
