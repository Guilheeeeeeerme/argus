# Argus — deployment

Production APIs and workers run on the Hostinger VPS through Dokploy. The database remains **Supabase Postgres**, schema `argus`; frames use private **Cloudflare R2** storage. Admin and triage SPAs run on Cloudflare Pages. This repository owns the application workflows and Compose; infra owns shared host operations.

## What runs where

| Place | What |
| --- | --- |
| GitHub Actions (this repo) | **Deploy (Dokploy)** (`deploy.yml`) and **Pages (SPA)** (`pages.yml`) |
| GHCR | `ghcr.io/guilheeeeeeerme/argus/<service>:<sha>` plus moving `:production` tags |
| VPS — Dokploy | `deploy/compose.prod.yml`: API, Celery worker, app-owned Redis and migration one-shot; profile `pipeline` adds gateway/sync, stream-prep, edge-cv and prompt-eval |
| Supabase Postgres | Schema `argus`; owner `argus` for migrations, runtime `argus_app` with NOBYPASSRLS |
| Cloudflare R2 | Private `argus-frames` bucket via S3-compatible API |
| Cloudflare Pages | `argus-app` → `app.argus.ferredemo.dev`; `argus-triage` → `triage.argus.ferredemo.dev` |
| VPS Traefik | `api.argus.ferredemo.dev` → API |
| Gemini / JEV | Public provider APIs; Gemini VLM plus JEV post-VLM verification under `JEV_VERIFY_MODE` |

Secrets belong in Dokploy's stack environment and GitHub repository secrets. Keep operator backups outside git. Never repoint production database URLs at VPS Postgres.

## Push → production

1. Push to `main`. **Deploy (Dokploy)** resolves the release SHA, runs its DB-free API and pipeline service tests, builds/pushes GHCR images and runs a temporary Compose smoke on the GitHub runner.
2. Runner smoke checks core API/worker/migration startup and `/version`; its `pipeline` profile is off, so smoke does not prove camera-to-triage processing.
3. After smoke passes, CI calls the Dokploy webhook and polls the public API `/version` for the released SHA.
4. Independently, **Pages (SPA)** builds and publishes admin/triage. Configure `DOKPLOY_DEPLOY_HOOK_URL`, `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` repository secrets as described in [deploy/README.md](../deploy/README.md).

Manual triggers are in this repo's Actions tab. The optional `sha` selects the release; Pages has its own optional `sha` and must be coordinated separately for rollback.

After deployment, verify `/version`, database readiness, each expected container and pipeline consumer activity. HTTP availability alone does not prove a working camera, frame sampling, Gemini/JEV calls, or generated triage cases. Enable the `pipeline` profile when deploying those services; inspect their actual runtime status rather than inferring it from Compose definitions.

## Schema changes (Alembic)

Add revisions under `apps/api/alembic/`. The `migrate` one-shot uses `ADMIN_DATABASE_URL` to run `alembic upgrade head`, then reapplies `argus_app` grants. Dependent services start after successful migration. `SKIP_S3_BOOTSTRAP=1` skips object-store bootstrap for R2; `SEED_DEMO` is a separate explicit seed setting. The API and worker do not migrate on startup.

## Rollback

Use **Deploy (Dokploy)** with the previous good `sha`. For a schema-compatible rollback, set `SKIP_MIGRATIONS=1` in Dokploy first; it skips the whole migration/grants/bootstrap script, then remove it after rollback. A database-breaking migration requires a reviewed database rollback as well. Deploy the matching frontend SHA through **Pages (SPA)**. See [deploy/README.md](../deploy/README.md).

## Frame access

Production frames are private R2 objects. The UI uses the authenticated API route `/v1/accounts/{account_id}/cameras/{camera_id}/latest-frame`, which enforces account access and proxies frame bytes (with a gateway preview fallback). The retired `api.storage.argus.ferredemo.dev` hostname is not a required endpoint; do not add a public storage service to replace it. Local development continues to use MinIO.

## Local

```bash
cp .env.example .env.local.docker && cp .env.local.docker .env
./scripts/up.sh -d
```

Local Postgres is the Compose container. Production uses the existing Supabase database; local Compose does not change that ownership.

## Account/Unit rename (migration `014_rename_accounts_units`)

The release that renames Company → Account and Establishment → Unit changes
table and column names, RLS policies (`app.current_account_id`) and every API
path (`/v1/accounts/{id}/…`, `/v1/admin/accounts`, `/v1/auth/accounts`). The
previous application code cannot run against the migrated schema, so:

1. Deploy it with **Deploy (Dokploy)** and the migration one-shot enabled (Argus already
   migrates before rollout). Expect a short maintenance window between the
   migration and the new image starting.
2. Rollback = `alembic downgrade 013_public_app_grants` + deploy the previous
   SHA (the migration is fully reversible).
3. Old URLs answer **410 Gone** for one release (`argus/api/legacy.py`).
   Redis stream consumers accept the legacy `company_id` / `establishment_id`
   fields for one release; `deploy/ops/bootstrap.py` keeps working
   through the deprecated `CompanyUser` / `set_session_context(company_id=…)`
   aliases, which are removed in the following release.
