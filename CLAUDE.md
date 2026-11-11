# CLAUDE.md — Argus

Multi-account vision platform (MVP): admin SSO host, near-realtime triage micro-frontend, and an AI pipeline that turns camera streams into operator-ready **TriageCases**.

Agent behavioral rules (including RTK): see [AGENTS.md](./AGENTS.md). UI: [STYLE_GUIDE.md](./STYLE_GUIDE.md). Guardrails: [docs/ai-engineering.md](./docs/ai-engineering.md), [apps/api/docs/guardrails.md](./apps/api/docs/guardrails.md).

## Live

| App | URL |
| --- | --- |
| Admin | https://app.argus.ferredemo.dev |
| Triage | https://triage.argus.ferredemo.dev |
| API | https://api.argus.ferredemo.dev |
| Frames | Authenticated API camera `latest-frame` route; private R2 objects |

Production deploys use this repo's **Deploy (Dokploy)** workflow (GitHub Actions → GHCR → Dokploy, `deploy/compose.prod.yml`) and **Pages (SPA)** workflow for admin/triage. Infra owns shared host operations. Production Postgres remains on the existing Supabase database (schema `argus`, runtime role `argus_app`). The `migrate` one-shot runs Alembic with `ADMIN_DATABASE_URL` before dependent services start. Local Compose uses its own Docker Postgres. See [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) and [deploy/README.md](./deploy/README.md).

## Layout

npm workspaces (`apps/*`, `apps/shared/*`, `packages/*`):

| Path | Role |
| --- | --- |
| `apps/api` | FastAPI (Python 3.12), SQLAlchemy async, Alembic, Celery |
| `apps/admin` | Vite/React admin + SSO host — react-router pages in `src/routes/*`, Drawer forms in `src/components/forms/*`, typed API in `src/api/`, session in `src/app/SessionProvider.tsx` |
| `apps/triage` | Vite/React triage MFE |
| `apps/shared/auth` | Shared auth client helpers |
| `packages/ui` | `@argus/design-system` |
| `packages/i18n` | Shared i18n |
| `services/stream-gateway` | go2rtc |
| `services/stream-prep` | Frame sample → S3-compatible storage (R2 production, MinIO local) → Redis `frames:ready` |
| `services/prompt-eval` | Multimodal PromptSet eval → Detection / TriageCase |

Pipeline design: `stream-gateway` → `stream-prep` → `prompt-eval` → `api` → admin / triage MFEs. Production requires the `pipeline` profile and running consumers; an API health response alone does not verify live frame processing.

## Stack

- FE: React 19, Vite, Tailwind, oxlint
- BE: FastAPI, Supabase Postgres + RLS + pgvector, Redis, R2 (MinIO for local development)
- LLM: Gemini VLM (public API via `GEMINI_BASE_URL`) plus JEV post-VLM verification under `JEV_VERIFY_MODE`

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

CI pre-deploy gates live in `.github/workflows/deploy.yml`: DB-free API contract/version tests, stream-prep tests and prompt-eval tests before image builds and runner smoke.

## Conventions

- Opaque Redis SSO + hash-token MFE handoff; tenant comes from the **session**, not client claims.
- UI only through `@argus/design-system` — see STYLE_GUIDE (no inline hex / ad-hoc CSS variables).
- Align LLM calls with the Promptdesk guardrails standard.
- MVP auth: mock Auth0 path (`AUTH0_USE_MOCK`); do not wire production Auth0 casually.
- Do not put API keys in prompts; do not log untrusted multimodal content beyond ids/statuses.
