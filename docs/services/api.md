# Service: api

Handoff spec for the MVP FastAPI application. Related: `docs/SPEC.md`,
`docs/ai-engineering.md`, `docs/realtime-page.md`,
`docs/services/prompt-eval.md`.

## Purpose

Tenant-aware HTTP API and WebSocket gateway: CRUD for the MVP domain model,
inbound **webhook** ingestion with Bearer tokens, and near-realtime fan-out of
detection / triage events to the triage MFE. Auth sessions, RLS, and SSO
handoff live here.

## Where it fits

```
Admin MFE  ──HTTP──►  API  ◄──HTTP──  Triage MFE
                        │
         WebhookEndpoint Bearer POST
                        │
                        ▼
              Redis: context:events ──► prompt-eval
                        │
   prompt-eval ── detections:positive ──► API (persist notify / WS)
                        │
                        ▼
              WS: detection.created / triage.updated
```

## Responsibilities

### CRUD (admin + triage)

- **Company**, **Establishment**, **Camera** (incl. stream config for gateway sync).
- **PromptSet / Prompt** and bindings.
- **Detection** (read; created by prompt-eval).
- **TriageCase** state transitions: `open` → `confirmed` | `dismissed` |
  `false_positive`.
- **Feedback** on cases (feeds RAG).
- **WebhookEndpoint** management (create/rotate Bearer secrets).

Internal: stream-gateway config sync (`GET /v1/internal/stream-configs` or
successor) with service token.

### Inbound webhooks

- `POST` to a public webhook path authenticated with the endpoint’s **Bearer
  token** (not a user session).
- Validate tenant + establishment (optional camera), persist **ContextEvent**,
  publish Redis `context:events`:

| Field | Notes |
|-------|-------|
| `company_id` | From endpoint binding |
| `establishment_id` | Required scope |
| `camera_id?` | Optional |
| `kind` | Event kind |
| `payload` | JSON body |
| `received_at` | Server time |
| `webhook_id` | Endpoint id |

### WebSocket

Authenticated with session token (`/v1/ws?token=...`), company-scoped rooms.

| Event | When |
|-------|------|
| `detection.created` | Positive detection + open TriageCase available |
| `triage.updated` | TriageCase state / feedback changed |

Also: `ready`, `heartbeat`, reconnect semantics for the triage rail.

## Auth (dev MVP)

- Opaque Redis sessions; `Authorization: Bearer <session>`.
- SSO host = admin app; MFEs use hash-token handoff + origin allow-list.
- Platform roles may switch active company/establishment; company roles may not.
- No production Auth0 (non-goal); mock/scaffold only.
- Webhooks: per-endpoint Bearer secret, distinct from user sessions.

## Non-responsibilities

- Frame sampling / MinIO TTL write path (stream-prep).
- VLM evaluation / negative discard (prompt-eval).
- SMS / Agent M2M / sketch editor / ROI / RuleSet / Recipe (out of MVP).
