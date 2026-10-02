# ARGUS MVP — Product Specification

Domain-agnostic multi-tenant vision platform. Cameras at units stream
through a media gateway; **stream-prep** turns live media into temporary frame
images; **prompt-eval** runs multimodal prompts and keeps only **positive**
detections (with a short evidence clip); operators triage cases in a dedicated
MFE. External systems inject context via inbound webhooks.

Product intent only. Service handoffs live under `docs/services/`; AI concept →
module mapping lives in `docs/ai-engineering.md`.

## Conceptual flow

```
Camera (RTSP config)
   │
   ▼
stream-gateway (go2rtc)     — restreams stable media endpoints
   │
   ▼
stream-prep                 — sample + preprocess frames → MinIO (TTL)
   │  Redis: frames:ready
   ▼
edge-cv (optional)          — motion + tracks + sensor fusion
   │  Redis: candidates:ready (EDGE_CV_ENABLED=true)
   ▼
prompt-eval                 — VLM + consensus; discard negatives
   │  Redis: detections:positive  (+ ContextEvent via context:events)
   ▼
API + Triage MFE            — TriageCase HITL; Feedback → RAG
```

1. A **Camera** at an **Unit** is restreamed by **stream-gateway**.
2. **stream-prep** samples frames, runs media preprocessing, stores ephemeral
   images in object storage (TTL), and publishes `frames:ready`.
3. With `EDGE_CV_ENABLED=true`, **edge-cv** consumes `frames:ready` and
   `context:events`, publishing ranked keyframes on `candidates:ready`.
   **prompt-eval** consumes those candidates and gates results using sensor,
   edge and VLM consensus. With the flag false it consumes `frames:ready`
   directly. It also consumes optional `context:events` and
   evaluates the active **PromptSet**, discards negatives, and on positive hits
   creates a **Detection** (clip ≤ 10 minutes) + open **TriageCase**.
4. Operators review cases in the triage MFE (`open` → `confirmed` /
   `dismissed` / `false_positive`) and leave **Feedback** that grounds future
   evaluations (pgvector RAG).

## Roles

| Role | Scope | Interface | Can switch account/unit? |
|------|-------|-----------|-----------------------------------|
| `root` | Platform | Admin | Yes; creates accounts + users |
| `admin` | Platform | Admin | Yes; creates accounts + users |
| `manager` | One account | Admin | No |
| `operator` | One account | Triage MFE | No |

## Core entities

- **Account** — tenant boundary (RLS-enforced). Owns units, cameras,
  prompt sets, webhook endpoints, detections, triage cases, feedback.
- **Unit** — physical site under a account. Cameras belong here.
- **Camera** — belongs to an unit. Stores industry-standard stream
  config (RTSP URL + credentials). Media access is abstracted by
  **stream-gateway** (go2rtc), which syncs configs from the API over an
  internal token-protected route.
- **PromptSet / Prompt** — versioned set of evaluation prompts bound to
  cameras or units. Each prompt defines what a positive hit means;
  multi-prompt evaluation runs the full set per sequence.
- **Detection** — **positive only**. Carries `prompt_hits`, confidence,
  summary, and an evidence **clip** (duration ≤ 10 minutes) stored in object
  storage. Negatives are discarded and never persisted as detections.
- **TriageCase** — operator work item linked to a detection. States:
  `open` → `confirmed` | `dismissed` | `false_positive`.
- **WebhookEndpoint / ContextEvent** — inbound HTTP webhooks (Bearer token)
  inject external context (`context:events` Redis stream). Events optionally
  scope to a camera; they ground prompt evaluation.
- **Feedback** — operator notes on a triage case; embedded and retrieved via
  RAG for future prompt-eval grounding.

## Redis contracts

### `frames:ready` (stream-prep → edge-cv / legacy prompt-eval)

| Field | Notes |
|-------|-------|
| `account_id` | Tenant |
| `unit_id` | Site |
| `camera_id` | Source camera |
| `sequence_id` | Frame sequence / window id |
| `captured_at` | Capture timestamp |
| `frame_uris[]` | Temporary frame object URIs (MinIO) |
| `preproc_meta` | Preprocessing metadata; `frames[].captured_at` preserves per-frame event time |

### `candidates:ready` (edge-cv → prompt-eval)

| Field | Notes |
|-------|-------|
| `account_id`, `unit_id`, `camera_id` | Original scoped frame identity |
| `sequence_id`, `captured_at` | Original sequence and capture time |
| `frame_uris[]` | At most K=3 ranked keyframe URIs; VLM uses one |
| `preproc_meta` | Selected-frame metadata |
| `edge_score`, `motion_score` | Finite normalized scores |
| `tracks[]` | Allowed-class track observations |
| `sensor_ids[]`, `sensors[]` | Scoped sensors matched by event time |
| `temporal_span_seconds` | Keyframe span |

Lists/objects are JSON-encoded Redis values. Group `edge-cv` reads frames and
context independently; group `prompt-eval` reads candidates when enabled.
See [edge-fusion-architecture.md](edge-fusion-architecture.md) for defaults and rollback.

### `context:events` (API webhooks → edge-cv / prompt-eval)

| Field | Notes |
|-------|-------|
| `account_id` | Tenant |
| `unit_id` | Site |
| `camera_id?` | Optional camera scope |
| `kind` | Event kind |
| `payload` | Opaque JSON payload |
| `received_at` | Ingest timestamp |
| `occurred_at` | Aware event timestamp; defaults to ingestion time |
| `role` | `trigger`, `filter`, `context` (default) |
| `confidence?` | Finite normalized sensor confidence |
| `context_event_id` | Persisted event identifier |
| `webhook_id` | Source WebhookEndpoint |

### `detections:positive` (prompt-eval → API / WS consumers)

| Field | Notes |
|-------|-------|
| `detection_id` | Created detection |
| `triage_case_id` | Open TriageCase |
| `clip_uri` | Evidence clip (≤ 10 min) |
| `prompt_hits[]` | Which prompts fired |
| `confidence` | Aggregate / primary confidence |
| `summary` | Short natural-language summary |

## Auth model (dev)

- Users: opaque Redis sessions, Bearer tokens, `POST /v1/auth/login` →
  `/v1/auth/me` → `PATCH /v1/auth/context` (platform roles only; sets
  active account/unit).
- SSO: admin app hosts login + `/sso/handoff`; MFEs receive `#token=` via
  origin-allowlisted return URLs (`SSO_RETURN_ORIGINS`).
- Isolation: PostgreSQL RLS — platform roles bypass; tenant roles scoped to
  the Redis session’s active account.
- Inbound webhooks: per-endpoint Bearer tokens (not user sessions).

## Non-goals (MVP)

- **Agent** (edge device / M2M agent model; VPS-colocated edge-cv is a service, not this entity)
- **Sketch** / floor-plan editor MFE
- **ROI** (drawn regions of interest)
- **RuleSet** / Rule / shift scheduling
- **Recipe** (AI analysis profile attached to rule sets)
- **SMS** / Twilio-style outbound notifications
- **Production Auth0** (scaffold/mock only; no production IdP)

Also out of scope for this MVP slice: TLS/edge gateway in local Compose;
per-service production deployables beyond what `infra` already owns.


### Redis contract compatibility (rename release)

Producers emit `account_id` / `unit_id`. Consumers (prompt-eval, edge-cv, the
API detections bridge and latest-frame reader) also accept the legacy field
names `company_id` / `establishment_id` for one release so in-flight messages
survive the rollout. The legacy readers are removed in the next release.
