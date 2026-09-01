# Data Model: ARGUS SaaS MVP

**Feature**: `001-saas-mvp` | **Date**: 2026-09-01

PostgreSQL schema for multi-tenant surveillance operations. All tenant-scoped tables
include `tenant_id` and are protected by Row-Level Security (RLS).

## Conventions

- Primary keys: `UUID` (`gen_random_uuid()`).
- Timestamps: `TIMESTAMPTZ`, always UTC.
- Soft deletes: `deleted_at TIMESTAMPTZ NULL` on configuration entities only.
- Enums: PostgreSQL `ENUM` types listed below.
- Every query from application code sets `SET LOCAL app.current_tenant_id = '<uuid>'`
  before accessing tenant-scoped tables.

## Enum Types

```sql
CREATE TYPE user_role AS ENUM ('root_admin', 'tenant_admin', 'watcher');
CREATE TYPE decision_state AS ENUM (
  'normal', 'weird', 'warning',
  'resolved_true_positive', 'resolved_false_positive', 'resolved_false_negative'
);
CREATE TYPE feedback_disposition AS ENUM (
  'true_positive', 'false_positive', 'false_negative'
);
CREATE TYPE notification_channel AS ENUM ('sms', 'whatsapp');
CREATE TYPE notification_status AS ENUM (
  'pending', 'sent', 'delivered', 'failed'
);
CREATE TYPE schedule_day AS ENUM (
  'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'
);
```

---

## Entity-Relationship Overview

```text
tenants
  ├── markets
  │     └── cameras
  │           └── regions_of_interest
  ├── context_modes
  │     ├── context_mode_schedules
  │     ├── context_mode_camera_assignments
  │     └── lenses
  ├── rules
  │     └── rule_region_mappings
  ├── evidences
  │     └── evidence_frames (→ S3 URIs)
  ├── decisions
  │     ├── decision_evidences (M:N)
  │     ├── feedback
  │     └── audit_records
  └── notification_configs
        └── notification_deliveries
```

---

## Core Tables

### `tenants`

Platform-level; RLS bypassed only by `root_admin` role.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Tenant identifier |
| name | VARCHAR(255) | NOT NULL | Display name |
| slug | VARCHAR(63) | UNIQUE NOT NULL | URL-safe identifier |
| aggregation_window_secs | INT | NOT NULL DEFAULT 300 | Decision grouping window (60–1800) |
| weird_threshold | INT | NOT NULL DEFAULT 2 | Evidence count → Weird |
| warning_threshold | INT | NOT NULL DEFAULT 5 | Cumulative severity → Warning |
| settings | JSONB | NOT NULL DEFAULT '{}' | Tenant-level config |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

### `tenant_users`

Maps IdP subject IDs to tenant + role. No passwords stored.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants, NULL for root_admin | NULL only when role = root_admin |
| idp_subject | VARCHAR(255) | NOT NULL | Auth0 `sub` claim |
| email | VARCHAR(255) | NOT NULL | From IdP; display/audit only |
| role | user_role | NOT NULL | RBAC role |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**Unique**: `(idp_subject, tenant_id)` — one role per tenant per user.

### `markets`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | |
| timezone | VARCHAR(63) | NOT NULL DEFAULT 'UTC' | For schedule evaluation |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| deleted_at | TIMESTAMPTZ | NULL | Soft delete |

**Index**: `(tenant_id)` WHERE `deleted_at IS NULL`

### `cameras`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants, NOT NULL | |
| market_id | UUID | FK → markets, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | |
| edge_device_id | VARCHAR(255) | NOT NULL | M2M client identifier |
| is_active | BOOLEAN | NOT NULL DEFAULT true | |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| deleted_at | TIMESTAMPTZ | NULL | |

**Unique**: `(tenant_id, edge_device_id)`

### `regions_of_interest`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants, NOT NULL | |
| camera_id | UUID | FK → cameras, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | e.g., "Entrance", "Aisle 3" |
| polygon | JSONB | NOT NULL | Normalized coordinates `[{x,y},...]` |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

---

## Context & Rules

### `context_modes`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | e.g., "Night Shift" |
| description | TEXT | NULL | |
| is_active | BOOLEAN | NOT NULL DEFAULT false | Manual override flag |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

### `context_mode_schedules`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants, NOT NULL | |
| context_mode_id | UUID | FK → context_modes, NOT NULL | |
| day_of_week | schedule_day | NOT NULL | |
| start_time | TIME | NOT NULL | Local to market timezone |
| end_time | TIME | NOT NULL | |
| market_id | UUID | FK → markets, NULL | NULL = all markets |

### `context_mode_camera_assignments`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants, NOT NULL | |
| context_mode_id | UUID | FK → context_modes, NOT NULL | |
| camera_id | UUID | FK → cameras, NOT NULL | |

**Unique**: `(camera_id)` — one active mode per camera at a time (enforced by
scheduler worker writing `camera_active_modes` cache).

### `lenses`

VLM prompt templates bound to a Context Mode.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants, NOT NULL | |
| context_mode_id | UUID | FK → context_modes, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | |
| system_prompt | TEXT | NOT NULL | Behavioral analysis instructions |
| output_schema | JSONB | NOT NULL | Expected VLM JSON response shape |
| version | INT | NOT NULL DEFAULT 1 | Immutable versions on edit |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

### `rules`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants, NOT NULL | |
| context_mode_id | UUID | FK → context_modes, NOT NULL | |
| name | VARCHAR(255) | NOT NULL | |
| condition | JSONB | NOT NULL | Structured rule definition |
| severity_weight | INT | NOT NULL DEFAULT 1 | Contributes to Decision score |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

### `rule_region_mappings`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants, NOT NULL | |
| rule_id | UUID | FK → rules, NOT NULL | |
| region_id | UUID | FK → regions_of_interest, NOT NULL | |

**Unique**: `(rule_id, region_id)`

---

## Operational Data

### `evidences`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants, NOT NULL | |
| camera_id | UUID | FK → cameras, NOT NULL | |
| region_id | UUID | FK → regions_of_interest, NULL | |
| context_mode_id | UUID | FK → context_modes, NOT NULL | Active at capture time |
| captured_at | TIMESTAMPTZ | NOT NULL | Edge-reported timestamp |
| received_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | Ingestion time |
| vlm_result | JSONB | NOT NULL | Parsed VLM response |
| severity_score | INT | NOT NULL | Derived from VLM + rules |
| frame_storage_uri | TEXT | NOT NULL | S3 URI for frame sequence |
| ingestion_id | UUID | NOT NULL | Idempotency key from edge |

**Index**: `(tenant_id, camera_id, captured_at)`
**Unique**: `(tenant_id, ingestion_id)` — idempotent ingestion

### `decisions`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants, NOT NULL | |
| camera_id | UUID | FK → cameras, NOT NULL | |
| region_id | UUID | FK → regions_of_interest, NULL | |
| state | decision_state | NOT NULL DEFAULT 'normal' | Lifecycle state |
| cumulative_severity | INT | NOT NULL DEFAULT 0 | Running score |
| evidence_count | INT | NOT NULL DEFAULT 0 | |
| window_start | TIMESTAMPTZ | NOT NULL | Aggregation window start |
| window_end | TIMESTAMPTZ | NOT NULL | Aggregation window end |
| first_evidence_at | TIMESTAMPTZ | NULL | |
| last_evidence_at | TIMESTAMPTZ | NULL | |
| resolved_at | TIMESTAMPTZ | NULL | |
| resolved_by | VARCHAR(255) | NULL | IdP subject of Watcher |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**Index**: `(tenant_id, state)` WHERE `state IN ('weird', 'warning')`

### `decision_evidences`

M:N join; immutable after link.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| decision_id | UUID | FK → decisions, NOT NULL | |
| evidence_id | UUID | FK → evidences, NOT NULL | |
| tenant_id | UUID | FK → tenants, NOT NULL | |
| linked_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**PK**: `(decision_id, evidence_id)`

### `feedback`

Append-only; no updates or deletes.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants, NOT NULL | |
| decision_id | UUID | FK → decisions, UNIQUE NOT NULL | One feedback per Decision |
| disposition | feedback_disposition | NOT NULL | |
| reasoning | TEXT | NOT NULL | Required for FP/FN |
| submitted_by | VARCHAR(255) | NOT NULL | IdP subject |
| embedding | vector(1536) | NULL | For RAG retrieval (pgvector) |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

### `audit_records`

Immutable append-only log for Constitution Principle VIII.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants, NOT NULL | |
| decision_id | UUID | FK → decisions, NOT NULL | |
| event_type | VARCHAR(63) | NOT NULL | e.g., `state_change`, `evidence_linked`, `resolved` |
| payload | JSONB | NOT NULL | Event details |
| actor | VARCHAR(255) | NULL | IdP subject or `system` |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

**No UPDATE/DELETE** granted to application role.

### `notification_configs`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants, NOT NULL | |
| channel | notification_channel | NOT NULL | |
| recipient | VARCHAR(63) | NOT NULL | E.164 phone number |
| is_active | BOOLEAN | NOT NULL DEFAULT true | |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

### `notification_deliveries`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | |
| tenant_id | UUID | FK → tenants, NOT NULL | |
| decision_id | UUID | FK → decisions, NOT NULL | |
| config_id | UUID | FK → notification_configs, NOT NULL | |
| channel | notification_channel | NOT NULL | |
| status | notification_status | NOT NULL DEFAULT 'pending' | |
| provider_message_id | VARCHAR(255) | NULL | Twilio SID |
| error_detail | TEXT | NULL | |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |
| updated_at | TIMESTAMPTZ | NOT NULL DEFAULT now() | |

---

## Row-Level Security

```sql
-- Enable on all tenant-scoped tables
ALTER TABLE markets ENABLE ROW LEVEL SECURITY;
-- ... repeat for every table with tenant_id

-- Standard tenant policy
CREATE POLICY tenant_isolation ON markets
  USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Root admin bypass (separate DB role)
CREATE POLICY root_admin_all ON markets
  USING (current_setting('app.current_role', true) = 'root_admin');
```

Application middleware flow:

1. Validate JWT → extract `tenant_id`, `role`, `sub`.
2. `SET LOCAL app.current_tenant_id = '<tenant_id>'`.
3. `SET LOCAL app.current_role = '<role>'`.
4. SQLAlchemy session executes queries; RLS enforces at DB level.

Edge ingestion uses M2M tokens scoped to `(tenant_id, camera_id)`; ingest API
validates token claims match payload `tenant_id` and `camera_id`.

---

## State Transitions: `decisions.state`

```text
normal ──(evidence_count >= weird_threshold)──► weird
weird  ──(cumulative_severity >= warning_threshold)──► warning
warning ──(Watcher resolves)──► resolved_true_positive | resolved_false_positive
any open state ──(Watcher reports missed threat)──► resolved_false_negative

Late evidence within open window: state may escalate (normal→weird→warning).
Closed resolved decisions: no re-opening; new evidence opens new Decision.
```

Optimistic locking: `decisions.updated_at` checked on Watcher resolve; concurrent
resolve returns `409 Conflict`.

---

## Redis Cache Keys

| Key Pattern | Purpose | TTL |
|-------------|---------|-----|
| `camera:active_mode:{camera_id}` | Current context mode ID | Refreshed by scheduler |
| `decision:open:{tenant_id}:{camera_id}:{region_id}` | Open Decision ID in window | aggregation_window_secs |
| `ws:room:{tenant_id}` | Pub/Sub channel for triage events | N/A |
| `ingest:idem:{tenant_id}:{ingestion_id}` | Idempotency guard | 24h |
