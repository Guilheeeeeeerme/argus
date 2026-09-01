# ARGUS

**Continuous vigilance. Simultaneous attention.**

> *Surveillance that never looks away.*

## About

ARGUS is a multi-tenant SaaS surveillance platform that watches many cameras at once — detecting anomalies, aggregating evidence, and alerting human watchers in real time.

Named after **Argos Panoptes** (Ἄργος Πανόπτης), the many-eyed sentinel of Greek mythology.

## Repository layout

| Path | Purpose |
|------|---------|
| `backend/` | Python FastAPI + Celery backend (7 deployables) |
| `specs/001-saas-mvp/` | Feature spec, plan, tasks, quickstart validation |
| `.specify/` | Spec Kit project config and constitution |

## Backend quick start

```bash
cd backend
cp .env.example .env
# Set DATABASE_URL, REDIS_URL, S3_*, AUTH0_* (see docs/auth0-setup.md)

docker compose -f docker/docker-compose.yml up -d postgres redis minio minio-init
ADMIN_DATABASE_URL=postgresql+asyncpg://argus:argus@localhost:5432/argus ./scripts/migrate.sh
PYTHONPATH=src python scripts/seed_dev.py

# Dev without Docker for all services:
pip install -e ".[dev]"
export PYTHONPATH=src AUTH0_USE_MOCK=true
pytest tests/ -q
```

### Service ports

| SERVICE_ROLE | Port | Description |
|--------------|------|-------------|
| `api-admin` | 8000 | Admin + Triage REST API |
| `api-ingest` | 8001 | Edge sequence ingestion |
| `ws-gateway` | 8002 | Real-time WebSocket triage |
| `worker-vlm` | — | VLM analysis (Celery) |
| `worker-aggregator` | — | Evidence aggregation |
| `worker-notify` | — | Twilio SMS/WhatsApp |
| `worker-scheduler` | — | Context mode schedules |

Start a service:

```bash
SERVICE_ROLE=api-admin PYTHONPATH=src python -m argus.main
```

Full stack: `docker compose -f backend/docker/docker-compose.yml up -d --build`

## Auth0

See [backend/docs/auth0-setup.md](backend/docs/auth0-setup.md) for tenant custom claims (`tenant_id`, `role`). Local dev can use `AUTH0_USE_MOCK=true`.

## Validation

MVP acceptance scenarios: [specs/001-saas-mvp/quickstart.md](specs/001-saas-mvp/quickstart.md)  
Latest run log: [specs/001-saas-mvp/validation-log.md](specs/001-saas-mvp/validation-log.md)

## License

TBD
