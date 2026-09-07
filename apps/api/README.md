# ARGUS API

FastAPI backend for the ARGUS platform. `SERVICE_ROLE` selects the runtime; compose
runs `api-admin` (:8000, `--reload`) and the Celery worker.

## Roles

`root` / `admin` (platform, RLS bypass via policy) · `manager` / `agent` (tenant-scoped via RLS).

## Auth

Opaque Redis sessions (`argus:session:{token}`, Bearer). Endpoints:

- `POST /v1/auth/login` — email + bcrypt password → `{ token, user, activeTenant, activeMarket }`
- `POST /v1/auth/logout`
- `GET /v1/auth/me`
- `PATCH /v1/auth/context` — platform only, sets `activeTenantId` / `activeMarketId`

Edge/agent devices use M2M client-credentials JWTs (`AUTH0_USE_MOCK=true` issues local
HS256 tokens; see `GET /v1/dev/session/edge`).

## Local commands (inside apps/api, or via compose)

```bash
alembic upgrade head          # migrations (007_rls policies use app.current_role IN ('root','admin'))
python scripts/seed.py        # idempotent dev seed (2 tenants, markets, users — Password123!)
python scripts/validate_rls.py
uvicorn argus.apps.http:create_admin_app --factory --reload
celery -A argus.workers.celery_app worker --beat --loglevel=INFO
```

Env: `DATABASE_URL` (app, RLS-enforced as `argus_app`), `ADMIN_DATABASE_URL` (migrations/seed as owner), `REDIS_URL`, `CORS_ORIGINS`, `DEV_JWT_SECRET` (mock M2M only).

Tests: `pytest tests/` (needs postgres + redis running).
