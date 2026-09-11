#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose up --build -d "$@"

echo "waiting for api health..."
for _ in $(seq 1 60); do
  if docker compose exec -T api python -c "import urllib.request; urllib.request.urlopen('http://api:8000/health').read()" >/dev/null 2>&1; then
    echo "api is up."
    break
  fi
  sleep 2
done

cat <<'EOF'

ARGUS dev stack:
  Admin (SSO host)  http://localhost:8180
  Triage MFE        http://localhost:8181
  API               http://localhost:8800  (health: /health)
  Postgres          postgres:5432 (argus/argus)
  Redis             redis:6379

Platform + demo users (password: Password123! when DEMO_PASSWORD unset)
  root@argus.local             (ROOT — platform)
  manager@demo.argus.local     (MANAGER — demo-retail)
  guest@demo.argus.local       (OPERATOR — demo-retail)
  Set SEED_DEMO=1 (default in compose) for demo fixtures.
EOF
