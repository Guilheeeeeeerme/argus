# ARGUS MVP — Product Specification

Domain-agnostic multi-tenant vision platform. Cameras at establishments stream
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
prompt-eval                 — VLM multi-prompt eval; discard negatives
   │  Redis: detections:positive  (+ ContextEvent via context:events)
   ▼
API + Triage MFE            — TriageCase HITL; Feedback → RAG
```

1. A **Camera** at an **Establishment** is restreamed by **stream-gateway**.
2. **stream-prep** samples frames, runs media preprocessing, stores ephemeral
   images in object storage (TTL), and publishes `frames:ready`.
3. **prompt-eval** consumes `frames:ready` (and optional `context:events`),
   evaluates the active **PromptSet**, discards negatives, and on positive hits
   creates a **Detection** (clip ≤ 10 minutes) + open **TriageCase**.
4. Operators review cases in the triage MFE (`open` → `confirmed` /
   `dismissed` / `false_positive`) and leave **Feedback** that grounds future
   evaluations (pgvector RAG).

## Roles

| Role | Scope | Interface | Can switch company/establishment? |
|------|-------|-----------|-----------------------------------|
| `root` | Platform | Admin | Yes; creates companies + users |
| `admin` | Platform | Admin | Yes; creates companies + users |
| `manager` | One company | Admin | No |
| `operator` | One company | Triage MFE | No |

## Core entities

- **Company** — tenant boundary (RLS-enforced). Owns establishments, cameras,
  prompt sets, webhook endpoints, detections, triage cases, feedback.
- **Establishment** — physical site under a company. Cameras belong here.
- **Camera** — belongs to an establishment. Stores industry-standard stream
  config (RTSP URL + credentials). Media access is abstracted by
  **stream-gateway** (go2rtc), which syncs configs from the API over an
  internal token-protected route.
- **PromptSet / Prompt** — versioned set of evaluation prompts bound to
  cameras or establishments. Each prompt defines what a positive hit means;
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

### `frames:ready` (stream-prep → prompt-eval)

| Field | Notes |
|-------|-------|
| `company_id` | Tenant |
| `establishment_id` | Site |
| `camera_id` | Source camera |
| `sequence_id` | Frame sequence / window id |
| `captured_at` | Capture timestamp |
| `frame_uris[]` | Temporary frame object URIs (MinIO) |
| `preproc_meta` | Preprocessing metadata from stream-prep |

### `context:events` (API webhooks → prompt-eval)

| Field | Notes |
|-------|-------|
| `company_id` | Tenant |
| `establishment_id` | Site |
| `camera_id?` | Optional camera scope |
| `kind` | Event kind |
| `payload` | Opaque JSON payload |
| `received_at` | Ingest timestamp |
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
  active company/establishment).
- SSO: admin app hosts login + `/sso/handoff`; MFEs receive `#token=` via
  origin-allowlisted return URLs (`SSO_RETURN_ORIGINS`).
- Isolation: PostgreSQL RLS — platform roles bypass; tenant roles scoped to
  the Redis session’s active company.
- Inbound webhooks: per-endpoint Bearer tokens (not user sessions).

## Non-goals (MVP)

- **Agent** (edge device / M2M agent model)
- **Sketch** / floor-plan editor MFE
- **ROI** (drawn regions of interest)
- **RuleSet** / Rule / shift scheduling
- **Recipe** (AI analysis profile attached to rule sets)
- **SMS** / Twilio-style outbound notifications
- **Production Auth0** (scaffold/mock only; no production IdP)

Also out of scope for this MVP slice: TLS/edge gateway in local Compose;
per-service production deployables beyond what `infra` already owns.
