# AI engineering map (MVP)

Maps each AI concept used by Argus MVP to the owning service and Python module
path. Product entities and Redis contracts live in `docs/SPEC.md`.

| Concept | Service | Python module |
|---------|---------|---------------|
| Media preprocessing | stream-prep | `argus_stream_prep.preprocessing` |
| Temporal windowing | stream-prep + prompt-eval | `temporal_window` |
| Multimodal VLM prompting | prompt-eval | `vlm` |
| Structured output | prompt-eval | `structured_output` |
| Multi-prompt evaluation | prompt-eval | `prompt_set_eval` |
| Context grounding | prompt-eval | `context_grounding` |
| Negative discard | prompt-eval | `negative_discard` |
| Evidence retention | prompt-eval | `evidence_retention` |
| RAG (pgvector) | prompt-eval (+ API write path) | `rag` |
| Prompt fencing / screening | prompt-eval | `guardrails` |
| Provider failover + budgets | prompt-eval | `provider_router` |
| HITL triage loop | api + triage MFE | API triage routes + triage workspace |

## Notes by concept

### Media preprocessing — `argus_stream_prep.preprocessing`

Runs inside **stream-prep** after frame sampling from go2rtc. Normalizes /
enriches frames before upload; metadata lands in `frames:ready.preproc_meta`.

### Temporal windowing — `temporal_window`

Shared concern: stream-prep chooses which frames belong to a sequence window;
prompt-eval may re-window or extend the clip around positive hits (clip ≤ 10
minutes). Module name is `temporal_window` in both services where applicable.

### Multimodal VLM prompting — `vlm`

Gemini-first multimodal calls over frame URIs (and optional clip). Prompt text
is fenced; untrusted context/feedback is screened before inclusion.

### Structured output — `structured_output`

Forces allowlisted JSON schemas from the VLM (prompt hits, confidence,
summary). Invalid shapes are rejected or retried, never stored as detections.

### Multi-prompt evaluation — `prompt_set_eval`

Evaluates the full active **PromptSet** for a sequence. Aggregates
`prompt_hits[]` for positive detections.

### Context grounding — `context_grounding`

Merges recent `context:events` (and retrieved RAG feedback) into the eval
context for the establishment/camera.

### Negative discard — `negative_discard`

If no prompt fires (or confidence floor fails), the sequence is dropped. No
Detection, no TriageCase, no `detections:positive` message.

### Evidence retention — `evidence_retention`

On positive hits, assemble and store the evidence clip (≤ 10 min) and retain
only what triage needs; temporary frames remain TTL-bound in MinIO.

### RAG (pgvector) — `rag`

Embeddings over Feedback / confirmed cases; retrieval feeds
`context_grounding`. Persistence is via API/Postgres; consumption is in
prompt-eval.

### Prompt fencing / screening — `guardrails`

OWASP-style mitigations: fence untrusted user/webhook content in the user
message; screen at write and before LLM; no tool-calling agency in MVP.

### Provider failover + budgets — `provider_router`

Provider order (default Gemini → optional OpenAI), per-tenant/global Redis
budgets, cheapest-first model rank and cross-provider failover after exhausted
attempts.

### HITL triage loop — api + triage MFE

API owns TriageCase CRUD/state transitions and WebSocket fan-out
(`detection.created`, `triage.updated`). Triage MFE is the operator surface;
Feedback writes close the loop into RAG.
