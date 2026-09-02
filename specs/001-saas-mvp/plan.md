# Implementation Plan: ARGUS SaaS MVP

**Branch**: `001-saas-mvp` | **Date**: 2026-09-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-saas-mvp/spec.md`

## Summary

ARGUS MVP delivers a multi-tenant surveillance triage platform: edge-filtered frame
sequences are ingested asynchronously, analyzed by a VLM against tenant-configured
Context Modes and Lenses, aggregated into Decisions with a state machine
(Normal → Weird → Warning → Resolved), pushed to Watchers via WebSocket, and
alerted off-site via Twilio — all with SSO-only auth, strict tenant isolation,
and immutable audit trails.

**Technical approach**: Python 3.12 / FastAPI micro-deployables, PostgreSQL with
RLS + pgvector, Redis Streams + Celery workers, S3 frame storage, Auth0 JWT,
OpenAI GPT-4o vision, Twilio notifications.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 (async), Alembic, Celery 5,
redis-py, httpx, PyJWT, python-jose, boto3, twilio, openai, pgvector

**Storage**: PostgreSQL 16 (relational + pgvector), Redis 7 (Streams, Pub/Sub,
Celery broker), S3-compatible object storage (frame blobs)

**Testing**: pytest, pytest-asyncio, httpx (API), factory-boy, testcontainers
(PostgreSQL + Redis)

**Target Platform**: Linux containers (Docker Compose dev, ECS/Kubernetes prod)

**Project Type**: Web service (decoupled backend deployables + separate SPAs)

**Performance Goals**:
- Ingestion endpoint: p95 < 100ms (202 response, enqueue only)
- Triage state propagation: < 5s edge-to-Watcher (SC-003)
- 10+ concurrent Watchers per tenant without conflict (SC-004)

**Constraints**:
- No local passwords (Constitution II)
- No biometric processing (Constitution V)
- Notifications MUST NOT block triage pipeline (Constitution VI)
- Admin Dashboard and Triage SPA are separate deployables (Constitution III)

**Scale/Scope**: MVP target — 10 tenants, 100 cameras, 50 concurrent Watchers,
~1000 ingestions/hour/tenant peak

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Plan Compliance | Implementation |
|-----------|----------------|----------------|
| I. Multi-Tenant Isolation | PASS | RLS on all tables + JWT `tenant_id` middleware + M2M scoped tokens |
| II. Authentication & Identity | PASS | Auth0 SSO; no password tables; JWT validation fail-closed |
| III. Interface Decoupling | PASS | `api-admin` + `api-ingest` + `ws-gateway` separate from Triage SPA |
| IV. Edge-to-Cloud Cost Control | PASS | Ingestion accepts pre-filtered sequences only; immediate 202 |
| V. Privacy & LGPD | PASS | VLM Lens prohibits identity/biometrics; timestamp-only correlation |
| VI. Async Communications | PASS | Celery `worker-notify` on separate queue; no sync Twilio in hot path |
| VII. Continuous Improvement | PASS | Feedback table + pgvector RAG injected into VLM prompts |
| VIII. Traceability | PASS | `audit_records` append-only; `decision_evidences` immutable links |

**Post-design re-check**: All gates PASS. No violations requiring Complexity
Tracking justification.

## Architecture

### System Diagram

```text
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Edge Agent │────►│  api-ingest  │────►│ Redis Streams   │
│  (filtered) │ M2M │  (FastAPI)   │ 202 │ ingest:sequences│
└─────────────┘     └──────┬───────┘     └────────┬────────┘
                           │ S3 upload             │
                           ▼                       ▼
                    ┌──────────────┐     ┌─────────────────┐
                    │  S3 / MinIO  │     │  worker-vlm     │
                    │  (frames)    │◄────│  (Celery)       │
                    └──────────────┘     └────────┬────────┘
                                                  │
                           ┌──────────────────────┤
                           ▼                      ▼
                    ┌──────────────┐     ┌─────────────────┐
                    │  PostgreSQL  │◄────│ worker-aggregator│
                    │  (RLS)       │     │  (Celery)       │
                    └──────┬───────┘     └────────┬────────┘
                           │                      │
              ┌────────────┼──────────────┐        │
              ▼            ▼              ▼       ▼
       ┌───────────┐ ┌───────────┐ ┌──────────┐ ┌──────────────┐
       │ api-admin │ │ws-gateway │ │worker-   │ │worker-notify │
       │ (FastAPI) │ │(FastAPI)  │ │scheduler │ │(Twilio)      │
       └─────┬─────┘ └─────┬─────┘ └──────────┘ └──────────────┘
             │             │
             ▼             ▼
       ┌───────────┐ ┌───────────┐
       │  Admin    │ │  Triage   │
       │ Dashboard │ │    SPA    │
       │  (React)  │ │  (React)  │
       └───────────┘ └───────────┘
             │             │
             └──────┬──────┘
                    ▼
              ┌───────────┐
              │  Auth0    │
              │  (IdP)    │
              └───────────┘
```

### Deployable Services

| Service | Port | Scaling | Responsibility |
|---------|------|---------|----------------|
| `api-admin` | 8000 | Horizontal | Admin + Triage REST (config, resolve, playback) |
| `api-ingest` | 8001 | Horizontal (CPU) | Edge sequence ingestion, S3 upload, stream enqueue |
| `ws-gateway` | 8002 | Horizontal (connections) | Triage WebSocket fan-out via Redis Pub/Sub |
| `worker-vlm` | — | Horizontal (API rate) | VLM analysis of queued sequences |
| `worker-aggregator` | — | Horizontal | Evidence → Decision state machine |
| `worker-notify` | — | Horizontal (I/O) | Twilio SMS/WhatsApp dispatch |
| `worker-scheduler` | — | Single (Beat) | Context mode schedule activation |

All services share: PostgreSQL, Redis, S3. Each is a separate Docker image
built from `backend/` with `SERVICE_ROLE` env var selecting entrypoint.

---

## 1. Ingestion Pipeline

### Request Flow

```text
Edge POST /v1/ingest/sequences
  → Validate M2M JWT (tenant_id, camera_id claims)
  → Validate payload tenant_id/camera_id match token
  → Check idempotency key (ingestion_id) in Redis
  → Verify camera has active context_mode (Redis cache or DB)
  → Upload frames to S3: s3://{bucket}/{tenant_id}/{camera_id}/{ingestion_id}/
  → XADD ingest:sequences {payload_json}
  → Return 202 {ingestion_id, status: "queued"}
```

Total handler time target: < 100ms p95 (no VLM call in request path).

### Redis Stream Consumer (`worker-vlm`)

```text
XREADGROUP GROUP vlm-workers ingest:sequences
  → Deserialize job
  → Fetch active Lens for context_mode_id
  → Fetch top-5 similar Feedback embeddings (pgvector, same tenant+camera)
  → Construct VLM prompt:
      system: Lens.system_prompt + RAG feedback examples + "NEVER identify individuals"
      user: frame images (presigned S3 URLs) + region polygon + rules summary
  → Call OpenAI GPT-4o vision (structured JSON output per Lens.output_schema)
  → Parse response → compute severity_score from rules
  → INSERT evidences row
  → Enqueue aggregator task: aggregate_evidence.delay(evidence_id)
```

### VLM Response Schema (default Lens)

```json
{
  "is_suspicious": true,
  "behavior_summary": "Person lingering in restricted area for 45 seconds",
  "matched_rules": ["loitering", "after_hours_presence"],
  "confidence": 0.87,
  "severity_hint": 3
}
```

---

## 2. Aggregation & State Machine (`worker-aggregator`)

### Grouping Logic

```python
# Pseudocode — actual implementation in aggregator service
def aggregate(evidence):
    key = (evidence.tenant_id, evidence.camera_id, evidence.region_id)
    open_decision = redis.get(f"decision:open:{key}")

    if open_decision:
        decision = db.get(open_decision)
        if evidence.captured_at <= decision.window_end:
            link_evidence(decision, evidence)
        else:
            decision = create_new_decision(evidence)
    else:
        decision = create_new_decision(evidence)

    decision.evidence_count += 1
    decision.cumulative_severity += evidence.severity_score
    decision.last_evidence_at = evidence.captured_at

    new_state = compute_state(decision)  # normal→weird→warning thresholds
    if new_state != decision.state:
        old_state = decision.state
        decision.state = new_state
        write_audit_record(decision, "state_change", old_state, new_state)
        redis.publish(f"ws:room:{tenant_id}", state_changed_event)
        if new_state == "warning":
            notify_warning.delay(decision.id)

    db.commit()
```

### Thresholds (tenant-configurable)

| Transition | Default Condition |
|------------|-------------------|
| normal → weird | `evidence_count >= tenant.weird_threshold` (default 2) |
| weird → warning | `cumulative_severity >= tenant.warning_threshold` (default 5) |

### Out-of-Order Handling

- Window boundaries determined by `captured_at`, not `received_at`.
- Late evidence within `window_end` merges into open Decision.
- Late evidence after `window_end` creates new Decision if severity warrants.

---

## 3. Notification Worker (`worker-notify`)

```text
Celery task: notify_warning(decision_id)
  → Load decision + tenant notification_configs (active)
  → For each config:
      → Create notification_deliveries row (status: pending)
      → Call Twilio API (SMS or WhatsApp)
      → Update status: sent | failed
      → On failure: log error_detail, retry with exponential backoff (max 3)
  → NEVER modify decision.state or block aggregator
```

Twilio integration isolated in `argus.integrations.twilio_client.TwilioNotifier`.

---

## 4. Identity & Security

### Auth0 Integration Flow

```text
1. User visits Admin Dashboard or Triage SPA
2. SPA redirects to Auth0 Universal Login (OIDC Authorization Code + PKCE)
3. Auth0 returns ID token + access token to SPA
4. SPA sends Bearer token on API requests / WS connection
5. Backend validates:
   - Signature (JWKS)
   - iss, aud, exp
   - Custom claims: tenant_id (uuid), role (enum)
6. Auth0 Action (post-login) maps user → tenant_users table role
```

### JWT Middleware (REST + WebSocket)

```python
# argus/core/auth.py — shared across all services
class AuthContext:
    sub: str          # IdP subject
    tenant_id: UUID
    role: UserRole    # root_admin | tenant_admin | watcher
    token: str

async def get_auth_context(request) -> AuthContext:
    token = extract_bearer(request)
    claims = validate_jwt(token, jwks_url=settings.AUTH0_JWKS_URL)
    return AuthContext(
        sub=claims["sub"],
        tenant_id=UUID(claims["tenant_id"]),
        role=UserRole(claims["role"]),
        token=token,
    )

# RBAC decorator
def require_role(*roles: UserRole):
  ...

# Tenant scoping — sets RLS context
async def set_tenant_context(session, auth: AuthContext):
    await session.execute(
        text("SET LOCAL app.current_tenant_id = :tid"),
        {"tid": str(auth.tenant_id)},
    )
    await session.execute(
        text("SET LOCAL app.current_role = :role"),
        {"role": auth.role.value},
    )
```

### Edge M2M Authentication

- Auth0 Machine-to-Machine application per edge deployment.
- Token claims: `tenant_id`, `camera_id`, `gty: client-credentials`.
- Ingest API rejects payload if claims ≠ body fields.

---

## 5. WebSocket Gateway

See [contracts/websocket-triage.md](./contracts/websocket-triage.md) for full
message contract.

Implementation highlights:
- FastAPI `@app.websocket("/v1/ws")` endpoint.
- On connect: validate JWT, join `triage:{tenant_id}` room.
- Background task: Redis SUBSCRIBE `ws:room:*`, forward to local connections.
- Decision resolve conflicts: REST endpoint uses optimistic locking (`updated_at`);
  WS broadcasts `decision.resolved` to all connected Watchers.

---

## Project Structure

```text
backend/
├── pyproject.toml
├── alembic/
│   ├── env.py
│   └── versions/
├── src/
│   └── argus/
│       ├── __init__.py
│       ├── main.py                    # Service entrypoint router (by SERVICE_ROLE)
│       ├── config.py                  # Pydantic Settings
│       ├── core/
│       │   ├── auth.py                # JWT validation, RBAC, tenant context
│       │   ├── database.py            # Async SQLAlchemy engine + session
│       │   ├── redis.py               # Redis client (Streams, Pub/Sub)
│       │   └── exceptions.py
│       ├── domain/
│       │   ├── models/                # SQLAlchemy ORM models
│       │   │   ├── tenant.py
│       │   │   ├── market.py
│       │   │   ├── camera.py
│       │   │   ├── context.py         # context_modes, lenses, rules, schedules
│       │   │   ├── evidence.py
│       │   │   ├── decision.py
│       │   │   ├── feedback.py
│       │   │   └── notification.py
│       │   ├── schemas/               # Pydantic request/response DTOs
│       │   └── enums.py
│       ├── api/
│       │   ├── admin/                 # api-admin routes
│       │   │   ├── router.py
│       │   │   ├── tenants.py
│       │   │   ├── markets.py
│       │   │   ├── cameras.py
│       │   │   ├── context_modes.py
│       │   │   ├── rules.py
│       │   │   └── notifications.py
│       │   ├── triage/                # Triage REST (on api-admin)
│       │   │   ├── router.py
│       │   │   ├── decisions.py
│       │   │   └── feedback.py
│       │   └── ingest/                # api-ingest routes
│       │       ├── router.py
│       │       └── sequences.py
│       ├── ws/
│       │   ├── gateway.py             # WebSocket connection manager
│       │   ├── handlers.py
│       │   └── pubsub.py              # Redis → WS fan-out
│       ├── workers/
│       │   ├── celery_app.py
│       │   ├── vlm_analyzer.py        # VLM analysis task
│       │   ├── aggregator.py          # Evidence → Decision state machine
│       │   ├── notifier.py            # Twilio dispatch task
│       │   └── scheduler.py           # Context mode activation (Beat)
│       ├── services/
│       │   ├── ingestion.py           # S3 upload + stream enqueue
│       │   ├── aggregation.py         # Decision grouping logic
│       │   ├── lens_builder.py        # Prompt construction + RAG
│       │   └── audit.py               # Append-only audit writer
│       └── integrations/
│           ├── auth0.py
│           ├── openai_vlm.py          # VLMClient protocol + GPT-4o impl
│           ├── twilio_client.py
│           └── s3_storage.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/
├── docker/
│   ├── Dockerfile.api-admin
│   ├── Dockerfile.api-ingest
│   ├── Dockerfile.ws-gateway
│   ├── Dockerfile.worker
│   └── docker-compose.yml
└── scripts/
    ├── seed_dev.py
    └── migrate.sh

frontend/                              # Out of MVP backend plan scope
├── admin-dashboard/                   # Separate React SPA
└── triage-spa/                        # Separate React SPA
```

**Structure Decision**: Monorepo with `backend/` containing all Python services
sharing domain models and core auth. Separate Docker images per deployable role.
Frontends are independent React SPAs (not detailed in this plan).

---

## Phase 0 & Phase 1 Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Research decisions | [research.md](./research.md) | Complete |
| Data model & schema | [data-model.md](./data-model.md) | Complete |
| Edge ingestion contract | [contracts/edge-ingestion.openapi.yaml](./contracts/edge-ingestion.openapi.yaml) | Complete |
| Admin & Triage REST | [contracts/admin-triage.openapi.yaml](./contracts/admin-triage.openapi.yaml) | Complete |
| WebSocket contract | [contracts/websocket-triage.md](./contracts/websocket-triage.md) | Complete |
| Validation guide | [quickstart.md](./quickstart.md) | Complete |

## Complexity Tracking

> No constitution violations. Table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Next Step

Run `/speckit-tasks` to generate dependency-ordered implementation tasks from
this plan.
