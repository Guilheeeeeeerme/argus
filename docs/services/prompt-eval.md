# Service: prompt-eval

Handoff spec for the MVP vision evaluation service. Related: `docs/SPEC.md`,
`docs/ai-engineering.md`, `docs/services/stream-prep.md`, `docs/services/api.md`.

## Purpose

Consume prepared frame sequences and optional context events, run multimodal
**PromptSet** evaluation (Gemini-first), **discard negatives**, and on positive
hits persist a **Detection** (evidence clip ≤ 10 minutes) plus an open
**TriageCase**, then announce via Redis for the API / realtime layer.

## Where it fits

```
stream-prep
   │  Redis: frames:ready
   ▼
prompt-eval (THIS SERVICE)
   │  also consumes Redis: context:events
   │  Gemini VLM + PromptSet
   │  negative → discard
   │  positive → Detection + clip + TriageCase
   │  Redis: detections:positive
   ▼
API / Triage MFE
```

## Inputs

### Redis stream `frames:ready`

From stream-prep: `company_id`, `establishment_id`, `camera_id`, `sequence_id`,
`captured_at`, `frame_uris[]`, `preproc_meta`.

### Redis stream `context:events`

From API inbound webhooks: `company_id`, `establishment_id`, optional
`camera_id`, `kind`, `payload`, `received_at`, `webhook_id`.

### Config / data plane

- Active **PromptSet / Prompt** bindings for the camera or establishment.
- RAG retrieval over prior **Feedback** (pgvector).
- Provider keys / budgets via `provider_router`.

## Outputs

### Persistence (via API DB / shared Postgres)

- **Detection** — positive only: `prompt_hits[]`, confidence, summary,
  `clip_uri` (duration ≤ 10 minutes).
- **TriageCase** — state `open`, linked to the detection.

### Redis stream `detections:positive`

| Field | Notes |
|-------|-------|
| `detection_id` | Created row |
| `triage_case_id` | Open case |
| `clip_uri` | Evidence clip |
| `prompt_hits[]` | Fired prompts |
| `confidence` | Score |
| `summary` | Short text |

Negatives produce **no** detection, **no** triage case, and **no**
`detections:positive` message (`negative_discard`).

## Pipeline (modules)

1. Consume `frames:ready` (+ recent `context:events`).
2. `temporal_window` — align / extend window for clip assembly.
3. `context_grounding` + `rag` — attach webhook context and retrieved feedback.
4. `guardrails` — fence/screen untrusted text before prompting.
5. `prompt_set_eval` → `vlm` (Gemini) → `structured_output`.
6. `provider_router` — failover + budgets on provider errors / spend.
7. `negative_discard` — drop non-hits.
8. `evidence_retention` — build ≤ 10 min clip; emit Detection + TriageCase;
   publish `detections:positive`.

## Non-responsibilities

- Frame sampling from go2rtc (stream-prep).
- CRUD admin surfaces, webhook HTTP ingress, WS fan-out (API).
- Operator UI (triage MFE).
- SMS / RuleSet / Recipe / ROI (out of MVP).
