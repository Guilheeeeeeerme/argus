#!/bin/sh
set -e
echo "[entrypoint] alembic upgrade head"
alembic upgrade head
echo "[entrypoint] platform bootstrap"
python scripts/seed_platform.py
case "${SEED_DEMO:-0}" in
  1|true|TRUE|yes|YES)
    echo "[entrypoint] seeding demo data (SEED_DEMO)"
    python scripts/seed_demo.py
    ;;
  *)
    echo "[entrypoint] skipping demo seed (SEED_DEMO unset)"
    ;;
esac
exec "$@"
