#!/bin/sh
set -e
echo "[entrypoint] alembic upgrade head"
alembic upgrade head
echo "[entrypoint] seeding dev data"
python scripts/seed.py
exec "$@"
