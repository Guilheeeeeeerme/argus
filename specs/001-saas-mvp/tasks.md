# Tasks: ARGUS SaaS MVP

**Input**: Design documents from `/specs/001-saas-mvp/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tasks grouped by deployable build phase (Foundation → Ingestion → Processing → Management). Each task tagged with target deployable `[infra]`, `[api-ingest]`, `[worker-vlm]`, `[worker-aggregator]`, `[worker-scheduler]`, `[api-admin]`, `[ws-gateway]`, or `[worker-notify]`. User story labels `[US1]`–`[US6]` added where applicable.

## Format

```text
- [ ] T### [P?] [Deployable] [US?] Description. **Done**: validation criteria
```

---

## Phase 1: Foundation

**Purpose**: Local orchestration, shared libraries, database schema with RLS, Auth0 JWT middleware. **No business-logic endpoints until T018 passes.**

**Checkpoint**: `docker compose up` healthy; `alembic upgrade head` succeeds; JWT middleware unit-verified; RLS blocks cross-tenant SELECT.

### 1.1 Project & Local Orchestration

- [x] T001 [infra] Create `backend/` directory tree per plan.md (`src/argus/`, `tests/`, `docker/`, `alembic/`, `scripts/`). **Done**: `tree backend/src/argus` matches plan structure.

- [x] T002 [infra] Create `backend/pyproject.toml` with Python 3.12, FastAPI, SQLAlchemy 2.0 async, Alembic, Celery, redis, httpx, PyJWT, boto3, twilio, openai, pgvector dependencies. **Done**: `cd backend && pip install -e .` exits 0.

- [x] T003 [infra] Create `backend/.env.example` documenting all required env vars (`DATABASE_URL`, `REDIS_URL`, `S3_*`, `AUTH0_*`, `OPENAI_API_KEY`, `TWILIO_*`, `SERVICE_ROLE`). **Done**: every key referenced in `config.py` is documented.

- [x] T004 [infra] Implement `backend/src/argus/config.py` Pydantic Settings loading from env. **Done**: `python -c "from argus.config import settings; print(settings)"` prints without error.

- [x] T005 [infra] Create `backend/docker/docker-compose.yml` with PostgreSQL 16 (+ pgvector image), Redis 7, MinIO, and placeholder services for all 7 deployables (ports 8000–8002 exposed). **Done**: `docker compose -f backend/docker/docker-compose.yml up -d postgres redis minio` → all healthy.

- [x] T006 [P] [infra] Create `backend/docker/Dockerfile.api-admin`, `Dockerfile.api-ingest`, `Dockerfile.ws-gateway`, `Dockerfile.worker` (shared worker image, `SERVICE_ROLE` selects worker type). **Done**: `docker build -f backend/docker/Dockerfile.worker backend/` succeeds.

- [x] T007 [infra] Implement `backend/src/argus/main.py` entrypoint routing by `SERVICE_ROLE` env to admin, ingest, ws, or worker apps. **Done**: `SERVICE_ROLE=api-admin python -m argus.main` starts without import errors.

### 1.2 Database Schema & Migrations

- [x] T008 [infra] Initialize Alembic in `backend/alembic/` with async SQLAlchemy support in `alembic/env.py`. **Done**: `alembic current` runs against local Postgres.

- [x] T009 [infra] Migration `001_enums`: create PostgreSQL ENUMs (`user_role`, `decision_state`, `feedback_disposition`, `notification_channel`, `notification_status`, `schedule_day`) in `backend/alembic/versions/001_enums.py`. **Done**: `alembic upgrade head`; `\dT` in psql lists all enums.

- [x] T010 [infra] Migration `002_core_tenancy`: `tenants`, `tenant_users` tables per data-model.md in `backend/alembic/versions/002_core_tenancy.py`. **Done**: tables exist; `tenant_users` has no password columns.

- [x] T011 [P] [infra] Migration `003_surveillance_config`: `markets`, `cameras`, `regions_of_interest` in `backend/alembic/versions/003_surveillance_config.py`. **Done**: FK chain `tenants → markets → cameras → regions_of_interest` verified.

- [x] T012 [P] [infra] Migration `004_context_rules`: `context_modes`, `context_mode_schedules`, `context_mode_camera_assignments`, `lenses`, `rules`, `rule_region_mappings` in `backend/alembic/versions/004_context_rules.py`. **Done**: all tables created with `tenant_id` NOT NULL.

- [x] T013 [infra] Migration `005_operational`: `evidences`, `decisions`, `decision_evidences`, `feedback`, `audit_records`, `notification_configs`, `notification_deliveries` in `backend/alembic/versions/005_operational.py`. **Done**: `decision_evidences` PK is `(decision_id, evidence_id)`; `feedback.decision_id` is UNIQUE.

- [x] T014 [infra] Migration `006_pgvector`: enable `vector` extension; add `feedback.embedding vector(1536)` column in `backend/alembic/versions/006_pgvector.py`. **Done**: `SELECT '[1,2,3]'::vector` succeeds.

- [x] T015 [infra] Migration `007_rls`: enable RLS on all tenant-scoped tables; create `tenant_isolation` and `root_admin_all` policies using `app.current_tenant_id` / `app.current_role` session vars in `backend/alembic/versions/007_rls.py`. **Done**: session with tenant A cannot SELECT tenant B rows; root_admin role can.

### 1.3 Shared Core Libraries

- [x] T016 [infra] Implement `backend/src/argus/core/database.py` async engine, session factory, `get_db` dependency. **Done**: async session connects and runs `SELECT 1`.

- [x] T017 [P] [infra] Implement `backend/src/argus/core/redis.py` async Redis client with helpers for Streams (`xadd`, `xreadgroup`), Pub/Sub, and key get/set in `backend/src/argus/core/redis.py`. **Done**: `redis-cli PING` via client returns `True`.

- [x] T018 [P] [infra] Implement `backend/src/argus/integrations/s3_storage.py` MinIO/S3 upload, presigned URL generation in `backend/src/argus/integrations/s3_storage.py`. **Done**: upload test file to `s3://argus-frames/test/` and generate presigned GET URL.

- [x] T019 [infra] Implement `backend/src/argus/domain/enums.py` mirroring PostgreSQL ENUMs. **Done**: all enum values match migration `001_enums`.

- [x] T020 [P] [infra] Implement ORM models `tenant.py`, `market.py`, `camera.py` in `backend/src/argus/domain/models/`. **Done**: models import; `tenant_id` present on all tenant-scoped models.

- [x] T021 [P] [infra] Implement ORM models `context.py` (modes, schedules, lenses, rules) in `backend/src/argus/domain/models/context.py`. **Done**: relationships to `Camera` and `ContextMode` resolve.

- [x] T022 [P] [infra] Implement ORM models `evidence.py`, `decision.py`, `feedback.py`, `notification.py` in `backend/src/argus/domain/models/`. **Done**: `Decision.evidences` M:N via `decision_evidences` association.

### 1.4 Auth0 & Security (BLOCKING)

- [x] T023 [infra] Document Auth0 setup in `backend/docs/auth0-setup.md`: tenant, API audience, custom claims Action (`tenant_id`, `role`), M2M app for edge, test users for each role. **Done**: doc covers all three roles + M2M flow.

- [x] T024 [infra] Implement `backend/src/argus/integrations/auth0.py` JWKS fetch/cache and JWT signature validation. **Done**: valid test token passes; expired token raises `401`.

- [x] T025 [infra] Implement `backend/src/argus/core/auth.py` `AuthContext`, `get_auth_context` dependency, `require_role(*roles)` decorator. **Done**: watcher token rejected on `require_role(tenant_admin)` with 403.

- [x] T026 [infra] Implement `set_tenant_context(session, auth)` executing `SET LOCAL app.current_tenant_id` and `SET LOCAL app.current_role` in `backend/src/argus/core/auth.py`. **Done**: after set, ORM query returns only own-tenant rows under RLS.

- [x] T027 [infra] Implement `backend/src/argus/core/exceptions.py` HTTP exception handlers (401, 403, 409, 422) registered on all FastAPI apps. **Done**: invalid JSON returns structured error body.

- [x] T028 [infra] Create `backend/scripts/seed_dev.py` inserting test tenant, market, camera, region, context mode, lens, rules, notification config, tenant_users. **Done**: `python scripts/seed_dev.py` exits 0; seed IDs printed.

- [x] T029 [infra] Create `backend/scripts/migrate.sh` wrapper for `alembic upgrade head`. **Done**: `./scripts/migrate.sh` applies all migrations on fresh DB.

**Phase 1 Gate**: T001–T029 complete. Auth middleware and RLS verified before any Phase 2 endpoint work.

---

## Phase 2: Core Ingestion

**Purpose**: `api-ingest` accepts edge sequences, uploads to S3, enqueues Redis Stream, returns 202 immediately.

**Goal (US3 partial)**: Edge → cloud ingestion path operational.

**Independent Test**: Mock POST to `/v1/ingest/sequences` → 202 ACK → message visible in `ingest:sequences` stream → frames in MinIO.

### 2.1 Ingestion Service

- [x] T030 [api-ingest] Create Pydantic schemas `IngestSequenceRequest`, `FramePayload`, `IngestAcceptedResponse` in `backend/src/argus/domain/schemas/ingest.py` matching `contracts/edge-ingestion.openapi.yaml`. **Done**: schema validates sample fixture JSON.

- [x] T031 [api-ingest] Implement M2M JWT validation dependency `get_edge_auth_context` extracting `tenant_id`, `camera_id` claims in `backend/src/argus/core/auth.py`. **Done**: user SSO token rejected; M2M token with matching claims accepted.

- [x] T032 [api-ingest] Implement `backend/src/argus/services/ingestion.py` `IngestionService`: validate camera active mode (Redis `camera:active_mode:{id}`), idempotency check (`ingest:idem:{tenant}:{ingestion_id}`), S3 upload, `XADD ingest:sequences`. **Done**: unit test mocks confirm call order; no DB write in hot path.

- [x] T033 [api-ingest] Create Redis Stream consumer group `vlm-workers` on `ingest:sequences` via init script `backend/scripts/init_redis_streams.py`. **Done**: `XINFO GROUPS ingest:sequences` shows `vlm-workers`.

- [x] T034 [api-ingest] Implement `POST /v1/ingest/sequences` in `backend/src/argus/api/ingest/sequences.py`: validate payload vs token claims, call `IngestionService`, return 202; 409 on duplicate `ingestion_id`. **Done**: `curl` mock POST returns 202 in <100ms; duplicate returns 409.

- [x] T035 [api-ingest] Implement `GET /v1/ingest/health` in `backend/src/argus/api/ingest/router.py`. **Done**: returns 200 `{"status":"ok"}`.

- [x] T036 [api-ingest] Wire `api-ingest` FastAPI app in `backend/src/argus/api/ingest/router.py`; register in `main.py` for `SERVICE_ROLE=api-ingest`. **Done**: service starts on port 8001 via docker compose.

- [x] T037 [api-ingest] Add `tests/fixtures/sample_ingest_payload.json` and reject-ingest test for camera with no active context mode (400). **Done**: POST without active mode returns 400 with clear error message.

**Phase 2 Checkpoint**: Send mock POST → 202 → `XREAD ingest:sequences` shows event → S3 object exists.

---

## Phase 3: Processing & Aggregation

**Purpose**: `worker-vlm` analyzes queued sequences; `worker-aggregator` groups Evidences into Decisions; `worker-scheduler` activates Context Modes on schedule.

**Goal (US2 partial, US3 complete)**: Full pipeline from stream message to Decision state in PostgreSQL.

**Independent Test**: Enqueue ingest job → Evidence row created → Decision row with correct state after N jobs.

### 3.1 Celery Infrastructure

- [x] T038 [worker-vlm] Implement `backend/src/argus/workers/celery_app.py` with Redis broker, task routes (`vlm`, `aggregate`, `notify`, `schedule` queues). **Done**: `celery -A argus.workers.celery_app inspect ping` returns worker response.

- [x] T039 [infra] Add `worker-vlm`, `worker-aggregator`, `worker-notify`, `worker-scheduler` services to `backend/docker/docker-compose.yml` sharing `Dockerfile.worker`. **Done**: all four workers start and connect to Redis broker.

### 3.2 VLM Analyzer Worker

- [x] T040 [worker-vlm] Implement `VLMClient` protocol and `OpenAIVLMClient` in `backend/src/argus/integrations/openai_vlm.py` with structured JSON output. **Done**: mock call returns parsed dict matching default Lens schema.

- [x] T041 [worker-vlm] Implement `backend/src/argus/services/lens_builder.py` `build_prompt(lens, rules, rag_feedback)`: inject "NEVER identify individuals" constraint (Constitution V). **Done**: output prompt contains biometrics prohibition string.

- [x] T042 [worker-vlm] Implement RAG retrieval in `backend/src/argus/services/lens_builder.py`: pgvector similarity query for top-5 feedback rows matching tenant+camera. **Done**: seeded feedback returned by similarity search.

- [x] T043 [worker-vlm] Implement `backend/src/argus/workers/vlm_analyzer.py` Celery task: consume stream via `XREADGROUP`, fetch Lens/rules, build prompt, call VLM, compute `severity_score`, INSERT `evidences`, enqueue `aggregate_evidence.delay(evidence_id)`. **Done**: one stream message → one `evidences` row; aggregator task queued.

- [x] T044 [worker-vlm] Add VLM failure handling in `vlm_analyzer.py`: retry 3x with backoff; dead-letter stream `ingest:dlq` on permanent failure. **Done**: forced VLM error lands message in DLQ after retries.

### 3.3 Evidence Aggregator Worker

- [x] T045 [worker-aggregator] Implement `backend/src/argus/services/audit.py` append-only `write_audit_record(decision, event_type, payload, actor)`. **Done**: INSERT only; UPDATE/DELETE on `audit_records` denied at DB level.

- [x] T046 [worker-aggregator] Implement `backend/src/argus/services/aggregation.py` `AggregationService.aggregate(evidence_id)`: window lookup by `captured_at`, open Decision via Redis `decision:open:{tenant}:{camera}:{region}`, link evidence, compute state transitions (normal→weird→warning). **Done**: 3 evidences in window → 1 decision with `evidence_count=3`.

- [x] T047 [worker-aggregator] Add out-of-order handling in `aggregation.py`: late `captured_at` within `window_end` merges; after `window_end` opens new Decision. **Done**: submit T+3min then T+1min evidences → both linked to same Decision.

- [x] T048 [worker-aggregator] Implement state-change side effects in `aggregation.py`: on transition publish Redis `PUBLISH ws:room:{tenant_id}` JSON envelope; on `warning` enqueue `notify_warning.delay(decision_id)`. **Done**: state change publishes message receivable via `redis-cli SUBSCRIBE`.

- [x] T049 [worker-aggregator] Implement `backend/src/argus/workers/aggregator.py` Celery task wrapping `AggregationService`. **Done**: `aggregate_evidence` task completes; Decision state persisted.

### 3.4 Context Mode Scheduler

- [x] T050 [worker-scheduler] Implement `backend/src/argus/workers/scheduler.py` Celery Beat task `activate_scheduled_modes`: evaluate `context_mode_schedules` against market timezones; write `camera:active_mode:{camera_id}` Redis keys; record audit log entry. **Done**: after schedule tick, `redis-cli GET camera:active_mode:{id}` returns correct mode UUID.

- [x] T051 [worker-scheduler] Configure Celery Beat schedule in `celery_app.py` (60s interval). **Done**: Beat process triggers `activate_scheduled_modes` every minute in logs.

**Phase 3 Checkpoint**: End-to-end: ingest POST → stream → VLM worker → evidence → aggregator → decision in `warning` state → Redis pub/sub event emitted.

---

## Phase 4: Management & Real-Time

**Purpose**: `api-admin` for configuration and triage REST; `ws-gateway` for live feed; `worker-notify` for Twilio alerts.

**Goal**: All six user stories independently testable per quickstart.md scenarios.

### 4.1 Multi-Tenant Admin (US1)

- [x] T052 [US1] [api-admin] Implement `POST /v1/admin/tenants` and `GET /v1/admin/tenants` in `backend/src/argus/api/admin/tenants.py` (root_admin only). **Done**: root_admin creates tenant; tenant_admin receives 403.

- [x] T053 [US1] [api-admin] Implement `POST /v1/admin/tenants/{tenant_id}/admins` assigning `tenant_users` row in `backend/src/argus/api/admin/tenants.py`. **Done**: assigned admin's JWT with `tenant_id` claim accesses only that tenant.

- [x] T054 [US1] [api-admin] Add cross-tenant guard middleware: reject path `tenant_id` mismatch vs JWT claim (except root_admin). **Done**: tenant A token on tenant B path returns 403 (quickstart Scenario 1).

### 4.2 Context & Rule Configuration (US2)

- [x] T055 [P] [US2] [api-admin] Implement `markets` CRUD routes in `backend/src/argus/api/admin/markets.py`. **Done**: tenant_admin creates market; appears in GET list.

- [x] T056 [P] [US2] [api-admin] Implement `cameras` and `regions` routes in `backend/src/argus/api/admin/cameras.py`. **Done**: region polygon stored; rule can reference `region_id`.

- [x] T057 [US2] [api-admin] Implement `context-modes`, `schedules`, `lenses` routes in `backend/src/argus/api/admin/context_modes.py`. **Done**: schedule created; mode activates after Beat tick (Scenario 2).

- [x] T058 [US2] [api-admin] Implement `rules` routes with `rule_region_mappings` in `backend/src/argus/api/admin/rules.py`. **Done**: rule mapped to specific region; visible in GET.

### 4.3 Triage REST (US4, US5)

- [x] T059 [US4] [api-admin] Implement `GET /v1/tenants/{tenant_id}/decisions` with state filter in `backend/src/argus/api/triage/decisions.py`. **Done**: returns active decisions for watcher token.

- [x] T060 [US4] [api-admin] Implement `GET /v1/tenants/{tenant_id}/decisions/{decision_id}` with linked evidences and presigned playback URLs in `backend/src/argus/api/triage/decisions.py`. **Done**: detail response includes evidence list and `playback_url`.

- [x] T061 [US5] [api-admin] Implement `POST /v1/tenants/{tenant_id}/decisions/{decision_id}/resolve` with optimistic locking (`updated_at`) in `backend/src/argus/api/triage/decisions.py`. **Done**: resolve returns 200; concurrent second resolve returns 409; audit record written.

- [x] T062 [US5] [api-admin] Implement feedback persistence in `backend/src/argus/api/triage/feedback.py`: store disposition, reasoning, generate pgvector embedding async. **Done**: feedback row linked to decision; embedding column populated.

- [x] T063 [US4] [api-admin] Wire `api-admin` FastAPI app combining admin + triage routers in `backend/src/argus/main.py` for `SERVICE_ROLE=api-admin`. **Done**: service starts on port 8000; OpenAPI docs list all routes.

### 4.4 WebSocket Gateway (US4)

- [x] T064 [US4] [ws-gateway] Implement connection manager in `backend/src/argus/ws/gateway.py`: tenant room map, max 5 connections per `sub`. **Done**: 6th connection from same sub rejected with close code 4008.

- [x] T065 [US4] [ws-gateway] Implement JWT validation on WebSocket handshake (`token` query param) in `backend/src/argus/ws/handlers.py`. **Done**: invalid token → close 4001; watcher token → joined room `triage:{tenant_id}`.

- [x] T066 [US4] [ws-gateway] Implement Redis Pub/Sub subscriber in `backend/src/argus/ws/pubsub.py` forwarding `decision.state_changed`, `decision.evidence_added`, `decision.resolved` envelopes per `contracts/websocket-triage.md`. **Done**: publish test message → connected client receives JSON within 1s.

- [x] T067 [US4] [ws-gateway] Implement heartbeat/pong (30s interval) in `backend/src/argus/ws/handlers.py`. **Done**: client receives `heartbeat` every 30s; `pong` response accepted.

- [x] T068 [US4] [ws-gateway] Wire `ws-gateway` app in `main.py` for `SERVICE_ROLE=ws-gateway` on port 8002. **Done**: `websocat` connects with valid watcher token (Scenario 5).

- [x] T069 [US4] [api-admin] Publish `decision.resolved` to Redis on resolve endpoint so all Watchers see update. **Done**: resolve via REST → all WS clients receive `decision.resolved` event.

### 4.5 External Notifications (US6)

- [x] T070 [US6] [api-admin] Implement `notification-configs` CRUD in `backend/src/argus/api/admin/notifications.py`. **Done**: tenant_admin adds SMS recipient; appears in GET.

- [x] T071 [US6] [worker-notify] Implement `TwilioNotifier` in `backend/src/argus/integrations/twilio_client.py` for SMS and WhatsApp send. **Done**: sandbox send returns Twilio SID (or mock in dev).

- [x] T072 [US6] [worker-notify] Implement `notify_warning` Celery task in `backend/src/argus/workers/notifier.py`: load configs, INSERT `notification_deliveries`, send async, update status, retry 3x on failure. **Done**: Warning decision triggers delivery row with `status=sent`; decision state unchanged on Twilio failure (Scenario 7).

- [x] T073 [US6] [api-admin] Implement `GET` notification delivery status per decision for tenant_admin review in `backend/src/argus/api/admin/notifications.py`. **Done**: failed delivery shows `error_detail`; independent from decision state.

**Phase 4 Checkpoint**: All quickstart.md Scenarios 1–7 pass against local docker compose stack.

---

## Phase 5: Polish & Cross-Cutting

**Purpose**: Hardening, documentation, full pipeline validation.

- [x] T074 [P] [infra] Add structured logging (JSON) across all deployables in `backend/src/argus/core/logging.py`. **Done**: log lines include `tenant_id`, `request_id`, `service_role`.

- [x] T075 [P] [infra] Add Redis idempotency TTL (24h) and open-decision key TTL aligned to `aggregation_window_secs` in `backend/src/argus/services/ingestion.py` and `aggregation.py`. **Done**: keys expire per tenant window config.

- [x] T076 [infra] Run full `specs/001-saas-mvp/quickstart.md` Scenarios 1–8 sequentially; document results in `specs/001-saas-mvp/validation-log.md`. **Done**: all scenarios pass or failures documented with remediation tasks.

- [x] T077 [P] [infra] Update root `README.md` with backend setup, docker compose commands, Auth0 config pointer, and service port map. **Done**: new developer can start stack from README alone.

---

## Dependencies & Execution Order

### Phase Dependencies

```text
Phase 1 (Foundation)
    │
    ▼
Phase 2 (api-ingest) ──requires── T016–T018, T025–T026, T032-context (Redis active mode from T050 OR manual seed)
    │
    ▼
Phase 3 (workers) ──requires── Phase 2 stream + S3 paths
    │
    ▼
Phase 4 (api-admin, ws-gateway, worker-notify) ──requires── Phase 3 decisions in DB
    │
    ▼
Phase 5 (Polish)
```

### Critical Path

```text
T001→T005→T008→T015→T023→T026 → T030→T034 → T038→T043→T049 → T052→T069 → T076
```

### User Story → Phase Mapping

| Story | Priority | Phase | Deployables |
|-------|----------|-------|-------------|
| US1 Multi-Tenant Setup | P1 | 4 | api-admin |
| US2 Context & Rules | P2 | 3+4 | worker-scheduler, api-admin |
| US3 Ingestion & Aggregation | P2 | 2+3 | api-ingest, worker-vlm, worker-aggregator |
| US4 Real-Time Triage | P1 | 4 | ws-gateway, api-admin |
| US5 Feedback | P2 | 4 | api-admin |
| US6 Notifications | P3 | 4 | worker-notify, api-admin |

### Parallel Opportunities

**Phase 1** (after T008):
```text
Parallel: T011 + T012 (config migrations)
Parallel: T020 + T021 + T022 (ORM models, after T019)
```

**Phase 3** (after T038):
```text
Parallel: T040–T044 (worker-vlm) ‖ T045–T049 (worker-aggregator) — different files; aggregator depends on evidences table populated by VLM
Sequential: VLM before aggregator in runtime, but development can proceed in parallel with mocked evidence inserts
```

**Phase 4** (after T054):
```text
Parallel: T055 + T056 (markets/cameras routes)
Parallel: T064–T068 (ws-gateway) ‖ T070–T072 (worker-notify) — no shared files
```

---

## Implementation Strategy

### MVP First (Ingestion + Triage path)

1. Complete Phase 1 (Foundation) — **mandatory gate**
2. Complete Phase 2 (api-ingest) — edge can submit sequences
3. Complete Phase 3 (workers) — decisions appear in DB
4. Complete Phase 4 minimal: T059–T061 (triage REST) + T064–T068 (ws-gateway)
5. **STOP and VALIDATE**: quickstart Scenarios 3–6
6. Add US1/US2 admin config (T052–T058) → Scenario 1–2
7. Add US6 notifications (T070–T072) → Scenario 7

### Suggested PR Boundaries

| PR | Tasks | Deployable(s) |
|----|-------|---------------|
| PR-1 | T001–T007 | infra |
| PR-2 | T008–T015 | infra |
| PR-3 | T016–T029 | infra |
| PR-4 | T030–T037 | api-ingest |
| PR-5 | T038–T044 | worker-vlm |
| PR-6 | T045–T051 | worker-aggregator, worker-scheduler |
| PR-7 | T052–T058 | api-admin |
| PR-8 | T059–T063 | api-admin |
| PR-9 | T064–T069 | ws-gateway |
| PR-10 | T070–T073 | worker-notify |
| PR-11 | T074–T077 | infra |

---

## Notes

- `[P]` = parallelizable (different files, no incomplete dependency)
- `[Deployable]` tag on every task for service ownership
- `[USn]` maps to spec.md user stories for traceability
- Auth0 + RLS (T023–T026) MUST complete before T034 (first business endpoint)
- No test tasks generated (not requested in spec); validation via **Done** criteria and quickstart.md
- Frontend SPAs (`admin-dashboard`, `triage-spa`) out of scope — backend tasks only
