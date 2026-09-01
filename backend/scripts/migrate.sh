#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
export DATABASE_URL="${ADMIN_DATABASE_URL:-postgresql+asyncpg://argus:argus@localhost:5432/argus}"
alembic upgrade head
