# ARGUS Backend

Python backend for the ARGUS SaaS surveillance platform. Seven containerized
deployables share this codebase; `SERVICE_ROLE` selects the runtime at startup.

## Services

| SERVICE_ROLE | Port | Description |
|--------------|------|-------------|
| `api-admin` | 8000 | Admin Dashboard + Triage REST API |
| `api-ingest` | 8001 | Edge sequence ingestion |
| `ws-gateway` | 8002 | Triage WebSocket gateway |
| `worker-vlm` | — | VLM analysis worker |
| `worker-aggregator` | — | Evidence aggregation worker |
| `worker-notify` | — | Twilio notification worker |
| `worker-scheduler` | — | Context mode schedule worker |

## Local development

```bash
cp .env.example .env
# Infrastructure only
docker compose -f docker/docker-compose.yml up -d postgres redis minio minio-init

# Migrations (superuser — from backend/)
ADMIN_DATABASE_URL=postgresql+asyncpg://argus:argus@localhost:5432/argus ./scripts/migrate.sh

# Verify RLS tenant isolation
PYTHONPATH=src python scripts/validate_rls.py

# Full stack (builds all 7 deployables)
docker compose -f docker/docker-compose.yml up -d --build

# Health checks
curl http://localhost:8000/health   # api-admin
curl http://localhost:8001/health   # api-ingest
curl http://localhost:8002/health   # ws-gateway
```

Python deps: `pip install -r requirements.txt` with `PYTHONPATH=src`, or `pip install -e .` in a venv.
