# Argus — deployment

Argus is **Hostinger-only**: everything runs on the VPS `82.25.74.147`
(`ferredemo.dev`). No Supabase, no Cloudflare. The build/deploy machinery lives
in the private **infra** repo; this page explains what happens when you push.

## What runs where

| Place | What |
| --- | --- |
| GitHub Actions (`infra` repo) | `Deploy app` / `Migrate app` workflows |
| GHCR | `ghcr.io/guilheeeeeeerme/argus/{api,worker,app,triage}:<appSha>.<infraSha>` |
| VPS — Compose project `argus` | `api` (FastAPI, loopback `18800`), `worker` (Celery + beat), `app` (admin SPA, `18180`), `triage` (MFE, `18181`) |
| VPS — shared `infra_data` | `postgres-argus` (roles `argus` owner / `argus_app` NOBYPASSRLS, DB `argus`, schema `argus`, pgvector), Redis DB `/1`, MinIO bucket `argus` |
| VPS — `infra_llm` | Headroom proxy (`LLM_USE_HEADROOM=true`, Gemini/OpenAI via `http://headroom:8787`) |
| VPS — nginx + Let's Encrypt | `api|app|triage.argus.ferredemo.dev` → loopback ports |
| Hostinger DNS | A records → VPS |

Secrets: `/opt/infra/secrets/argus.env` on the VPS, sourced from `infra/secrets/production.enc.yaml` (SOPS).

## Step by step: push → production

1. Push to `main`. `.github/workflows/deploy-infra.yml` sends `repository_dispatch`
   (`project=argus`, this repo, the commit SHA) to `infra` using secret `INFRA_DISPATCH_TOKEN`.
2. `infra` → **Deploy app**:
   1. `resolve`: SHA must be the current head of `main` (older pushes are skipped).
   2. `build` (GitHub runner): `scripts/app_test.sh argus` runs
      `pytest tests/test_http_cors.py tests/test_compose_contract.py`; `purge_gate.sh`
      rejects any Supabase reference; `build.sh` builds `api` (also tagged `worker`),
      `app` (`apps/admin`) and `triage` from `infra/containers/argus/*` and pushes to GHCR.
   3. `deploy` (VPS over SSH): `deploy.sh argus <release> deploy` — pulls the images,
      **checks Alembic is at head (fails closed if not)**, `docker compose up -d --wait`,
      smoke (`/health`, `/health/db`, app `/health`), promotes the release. Failure
      restores the previous release automatically.
3. Nothing else restarts: PromptDesk and Quizzeira are separate Compose projects.

Manual trigger: `infra` → Actions → **Deploy app** → `project=argus`, optional `sha`.

## Step by step: schema change (Alembic)

1. Add the revision under `apps/api/alembic/` and push.
2. In `infra`, run **Deploy app** with `migrate=true` (or **Migrate app** then **Deploy app**).
   On the VPS this runs `docker compose run --rm api alembic upgrade head`, re-grants
   `argus_app` on new tables (`postgres_ensure.py sync`), then `bootstrap.py`
   (root account + MinIO bucket). `seed_demo=true` adds `scripts/seed_demo.py`.
3. A plain deploy never migrates; the API image never migrates on start.

## Rollback

`infra` → **Deploy app** with the previous `sha`, or on the VPS:
`bash /opt/infra/repository/scripts/deploy.sh argus <previous release> rollback`.

## Local

```bash
cp .env.example .env.local.docker && cp .env.local.docker .env
./scripts/up.sh -d
```

Local Postgres is the Compose container; there is no remote-DB mode.
Full infra view: `infra/docs/DEPLOYMENT.md`.
