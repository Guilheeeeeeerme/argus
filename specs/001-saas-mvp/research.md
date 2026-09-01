# Research: ARGUS SaaS MVP

**Feature**: `001-saas-mvp` | **Date**: 2026-09-01

Phase 0 decisions resolving technical unknowns for the implementation plan.

---

## R1: Message Broker for Ingestion Offload

**Decision**: Redis Streams as the primary ingestion queue; Celery with Redis broker for
long-running worker tasks (VLM analysis, notifications).

**Rationale**:
- Redis is already required for WebSocket pub/sub and session state — single
  operational dependency.
- Redis Streams provide durable, consumer-group-based ingestion with sub-millisecond
  enqueue latency, satisfying the edge 202 response requirement.
- Celery handles retry semantics, task routing, and worker scaling for VLM calls
  (seconds-scale) and Twilio delivery without blocking the ingestion hot path.

**Alternatives considered**:
| Option | Rejected because |
|--------|------------------|
| RabbitMQ | Additional infrastructure; Redis already mandated |
| Celery-only for ingestion | Higher latency on enqueue; Streams better for fire-and-forget edge ACK |
| Kafka | Operational overhead disproportionate for MVP scale |

---

## R2: Multi-Tenant Isolation Strategy

**Decision**: Defense-in-depth — PostgreSQL Row-Level Security (RLS) as the database
enforcement layer, plus mandatory `tenant_id` filters in SQLAlchemy session scoping and
application middleware.

**Rationale**:
- Constitution Principle I requires isolation at every layer; RLS is the last line of
  defense against ORM bugs or raw SQL leaks.
- Application-level scoping (`SET app.current_tenant_id`) integrates with FastAPI
  dependency injection from JWT claims.
- Root Admin operations use a separate connection role with `BYPASSRLS` and explicit
  audit logging.

**Alternatives considered**:
| Option | Rejected because |
|--------|------------------|
| ORM-only scoping | Single missed filter causes cross-tenant leak |
| Schema-per-tenant | Migration and connection-pool explosion at scale |
| Database-per-tenant | Prohibitive ops cost for MVP |

---

## R3: Identity Provider

**Decision**: Auth0 as the MVP IdP.

**Rationale**:
- Mature JWT/OIDC support with custom claims (`tenant_id`, `role`) via Auth0 Actions.
- Machine-to-machine (M2M) client credentials for edge device authentication.
- Role-based access maps cleanly to Root Admin / Tenant Admin / Watcher.

**Alternatives considered**:
| Option | Rejected because |
|--------|------------------|
| Clerk | Strong for B2C; less mature M2M/edge device patterns |
| Keycloak (self-hosted) | Ops burden for MVP |
| Custom JWT | Violates Constitution Principle II |

---

## R4: VLM Provider

**Decision**: OpenAI GPT-4o (vision) as the MVP VLM; provider abstracted behind a
`VLMClient` protocol for future swap.

**Rationale**:
- Structured JSON output mode supports parseable severity/trigger responses.
- Lens (prompt) injection and RAG feedback retrieval compose naturally into the
  system prompt.
- No biometric extraction — VLM instructed to describe behavior only, never identify
  individuals (Constitution Principle V).

**Alternatives considered**:
| Option | Rejected because |
|--------|------------------|
| Google Gemini Vision | Viable fallback; OpenAI JSON mode more predictable for MVP |
| Self-hosted LLaVA | GPU ops out of MVP scope |
| Custom model training | Explicitly out of scope per spec |

---

## R5: Object Storage for Frame Sequences

**Decision**: S3-compatible object storage (AWS S3 or MinIO in dev) for frame blobs;
PostgreSQL stores metadata and references only.

**Rationale**:
- Base64 in ingestion payload accepted for MVP edge simplicity; API immediately
  offloads blobs to object storage before queueing analysis.
- Keeps PostgreSQL lean; audit trail references `s3://` URIs not raw bytes.
- Presigned URLs for Triage SPA evidence playback.

**Alternatives considered**:
| Option | Rejected because |
|--------|------------------|
| BYTEA in PostgreSQL | Table bloat, poor performance for video frames |
| Redis for blobs | Memory cost; TTL loss risks audit trail |

---

## R6: WebSocket Real-Time Delivery

**Decision**: Dedicated WebSocket Gateway service using FastAPI + `websockets`, with
Redis Pub/Sub for cross-instance fan-out.

**Rationale**:
- Constitution Principle III requires Triage SPA separation; WS gateway is a distinct
  deployable from Admin API.
- Redis Pub/Sub lets aggregator/VLM workers publish state transitions without knowing
  which gateway instance holds the Watcher connection.
- Tenant rooms keyed `triage:{tenant_id}`; JWT validated on handshake.

**Alternatives considered**:
| Option | Rejected because |
|--------|------------------|
| SSE on API server | Couples triage transport to Admin API process |
| Socket.IO | Heavier protocol; native WS sufficient |
| Polling | Violates SC-003 latency target |

---

## R7: Evidence Aggregation Algorithm

**Decision**: Time-windowed grouping keyed by `(tenant_id, camera_id, region_id)` with
sliding window; state machine driven by cumulative severity score.

**Rationale**:
- Spec default: 5-minute aggregation window, tenant-configurable 1–30 min.
- Out-of-order events: use `captured_at` timestamp (edge-reported), not `received_at`.
- Late arrivals within window merge into open Decision; closed windows create new
  Decision if severity warrants.

**Alternatives considered**:
| Option | Rejected because |
|--------|------------------|
| Fixed batch windows (tumbling only) | Edge case: event at window boundary splits incorrectly |
| Per-trigger Decision | Alert fatigue; violates FR-014 |
| Graph-based clustering | Over-engineered for MVP |

---

## R8: Notification Provider

**Decision**: Twilio for SMS and WhatsApp Business API.

**Rationale**:
- Single SDK for both channels per spec US6.
- Async Celery task with independent retry queue; failures logged to
  `notification_deliveries` table without touching Decision state.

**Alternatives considered**:
| Option | Rejected because |
|--------|------------------|
| AWS SNS | No native WhatsApp |
| Direct Meta WhatsApp API | Higher integration complexity vs Twilio wrapper |

---

## R9: RAG Feedback Retrieval

**Decision**: pgvector extension in PostgreSQL for embedding-based retrieval of past
Watcher feedback; embeddings generated at feedback write time via same VLM embedding
endpoint.

**Rationale**:
- Keeps feedback store co-located with tenant data (RLS applies).
- MVP scope: top-k similar false-positive/negative reasoning injected into VLM Lens
  prompt for same camera/market context.
- No custom model training — retrieval augments prompt only (Constitution VII).

**Alternatives considered**:
| Option | Rejected because |
|--------|------------------|
| Pinecone/Weaviate | Additional service for MVP |
| Keyword-only retrieval | Weaker contextual improvement signal |
| No RAG at MVP | Violates FR-025 utilization requirement |

---

## R10: Deployment Model

**Decision**: Containerized micro-deployables on a single orchestrator (Docker Compose
dev, ECS/Kubernetes prod):

| Service | Responsibility |
|---------|----------------|
| `api-admin` | Admin Dashboard REST API |
| `api-ingest` | Edge ingestion (high-throughput, separate scaling) |
| `ws-gateway` | Triage WebSocket connections |
| `worker-vlm` | Celery consumer: VLM analysis |
| `worker-aggregator` | Celery consumer: evidence → decision state machine |
| `worker-notify` | Celery consumer: Twilio dispatch |
| `worker-scheduler` | Celery Beat: context mode schedule activation |

**Rationale**:
- Ingestion and WebSocket scale independently from admin CRUD.
- Worker pools sized per workload (VLM is GPU/API-rate-bound; notify is I/O-bound).
- Shared PostgreSQL + Redis cluster.

**Alternatives considered**:
| Option | Rejected because |
|--------|------------------|
| Monolith | Cannot scale ingestion vs admin independently |
| Serverless-only | WebSocket + long VLM calls poorly suited to Lambda cold starts |
