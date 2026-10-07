#!/usr/bin/env bash
# One-shot production migration entrypoint. Runs in the `migrate` service
# (same image as api; baked at /app/deploy/migrate.sh) — NEVER inside api/worker
# containers (they never migrate on start).
#
# Order: alembic upgrade head (ADMIN_DATABASE_URL, owner role `argus`)
#        → re-apply argus_app role grants (deploy/ops/ensure_grants.py)
#        → platform bootstrap (root account + frame bucket)
#        → optional demo seed (SEED_DEMO).
set -euo pipefail

APP_ROOT="${APP_ROOT:-/app}"

if [ "${SKIP_MIGRATIONS:-0}" = "1" ] || [ "${SKIP_MIGRATIONS:-}" = "true" ]; then
  echo "[migrate] SKIP_MIGRATIONS=1 set — bypassing schema migration/grants"
  exit 0
fi

echo "[migrate] alembic upgrade head"
cd "${APP_ROOT}"
alembic upgrade head

echo "[migrate] ensure argus_app role grants"
python "${APP_ROOT}/deploy/ops/ensure_grants.py"

echo "[migrate] platform bootstrap (root account + frame bucket)"
python "${APP_ROOT}/deploy/ops/bootstrap.py"

case "${SEED_DEMO:-0}" in
  1|true|TRUE|yes|YES)
    echo "[migrate] seeding demo data (SEED_DEMO)"
    python "${APP_ROOT}/scripts/seed_demo.py"
    ;;
  *)
    echo "[migrate] skipping demo seed (SEED_DEMO unset)"
    ;;
esac

echo "[migrate] done"
