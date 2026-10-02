# prompt-eval

Multimodal **PromptSet** evaluation microservice. Consumes `frames:ready`,
grounds with `context:events` + RAG FP feedback, discards negatives, and on
positives persists Detection + open TriageCase then publishes
`detections:positive`.

See `docs/services/prompt-eval.md` and `docs/ai-engineering.md`.

## Layout

```
services/prompt-eval/
  requirements.txt
  Dockerfile
  README.md
  src/argus_prompt_eval/
    main.py                 # Redis consumer loops
    vlm.py                  # Multimodal VLM (Gemini + OpenAI)
    structured_output.py    # prompt_hits schema
    prompt_set_eval.py      # Multi-prompt evaluation
    context_grounding.py    # ContextEvents + RAG
    negative_discard.py     # drop negatives
    evidence_retention.py   # clip ≤10 min
    temporal_window.py      # window helpers
    rag.py                  # pgvector FP feedback
    guardrails.py           # fence / screen
    provider_router.py      # failover + budgets
    persist.py              # Detection + TriageCase
    redis_io.py             # streams I/O
    db.py                   # shared ORM import + RLS sessions
    _models_fallback.py     # mirrors if argus package absent
    config.py
    registry.yml
```

Each module docstring names the AI Engineering pattern it implements.

## Pipeline

1. `XREADGROUP frames:ready` (and `context:events`) consumer group `prompt-eval`
2. Load camera-bound PromptSet + enabled Prompts
3. `context_grounding` — recent ContextEvent rows + `rag` FP feedback
4. `prompt_set_eval` → `vlm.analyze` with structured schema
5. `negative_discard` when no hits clear `PROMPT_EVAL_CONFIDENCE_FLOOR`
6. `evidence_retention` — see clip strategy below
7. `persist` Detection + TriageCase(`open`) with RLS company context
8. `XADD detections:positive`

## Evidence clip strategy

| Mode | When | `clip_uri` | Notes |
|------|------|------------|-------|
| **ffmpeg mp4** | `ffmpeg` present (Docker installs it) | `s3://…/clips/….mp4` | Frames stitched ~1 fps |
| **frame URI list** | ffmpeg missing or stitch fails | first frame URI | Detection stores full `frame_uris[]` plus `window_started_at` / `window_ended_at` (≤ 10 min). Temporary frames stay TTL-bound in MinIO. |

## Environment

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres (asyncpg) |
| `REDIS_URL` | Redis streams |
| `S3_*` | MinIO / S3 for frames + clips |
| `GEMINI_*` / `OPENAI_*` | VLM providers |
| `LLM_PROVIDER_ORDER` | default `gemini,openai` |
| `LLM_*_BUDGET` / rate limits | provider budgets |
| `AUTH0_USE_MOCK` | mock VLM when no API keys |
| `MAX_CLIP_SECONDS` | default `600` (10 min) |

## Docker

Build context is the **repo root** (copies `apps/api/src/argus` + this service):

```bash
docker compose build prompt-eval
docker compose up prompt-eval
```

## Local run

```bash
cd services/prompt-eval
pip install -r requirements.txt
PYTHONPATH=src:../../apps/api/src python -m argus_prompt_eval
```

## Optional edge fusion

`EDGE_CV_ENABLED=false` (default) keeps the existing `frames:ready` path.
With `true`, prompt-eval consumes `candidates:ready` instead, in the same
`prompt-eval` consumer group, and continues consuming `context:events`.
Restart with the flag disabled to roll back.

Candidates retain `company_id`, `establishment_id`, `camera_id`, `sequence_id`,
`captured_at`, `frame_uris` and optional `preproc_meta`. They add `edge_score`,
`motion_score`, JSON arrays `tracks`, `sensor_ids`, `sensors`, and
`temporal_span_seconds`. Frames are ordered by descending track confidence;
only the first frame reaches the VLM. Structural JSON (`sensors`, `edge_tracks`,
`edge_score`) is screened and fenced as untrusted context. Malformed scores,
nonfinite values and mismatched sensor tenants are discarded before evaluation.
Sensor timestamps must be aware and within `EDGE_SENSOR_WINDOW_SECONDS` (default
5 seconds) of a selected frame; `preproc_meta.frames` follows selected frame
ordering. Full selected frames remain available for evidence retention.

A filter sensor vetoes when `payload.reject=true` or `payload.accepted=false`.
The strongest trigger confidence supplies the sensor score (missing confidence
or no trigger contributes zero). Matched VLM hits must first pass the existing
prompt confidence floor and negative-discard rules. The consensus gate then uses
`0.25 * sensor + 0.35 * edge + 0.40 * model >= 0.55`, or an existing prompt hit
with edge score at least `0.4`. `CONSENSUS_THRESHOLD` and
`CONSENSUS_EDGE_MINIMUM` override these two thresholds. Negatives never persist a
Detection/TriageCase or publish `detections:positive`. Provider routing, budgets,
frame URI validation and guardrails remain in the existing VLM path.

### Pending message recovery

The consumer reclaims stale pending entries from any consumer with `XAUTOCLAIM`
(Redis 6.2+), including entries left behind after a restart or provider outage.
`CONSUMER_RETRY_IDLE_MS` defaults to 300000 (five minutes). Each loop scans a
bounded pending batch and then reads new work; failed entries stay pending until
the next idle interval. The scan cursor advances so a failing oldest entry does
not starve the rest of the backlog.

Positive retries lock the tenant/camera/sequence within the database transaction
and reuse any committed Detection/TriageCase before evaluating again. A crash
between database commit and Redis publication/ACK therefore republishes the same
IDs. Stream publication remains at least once: consumers must deduplicate by
`detection_id`. Recovered publications contain persisted detection fields;
provider and ffmpeg metadata are only included on the original attempt.

Focused integration tests use explicitly disposable services via
`TEST_RECOVERY_REDIS_URL` and `TEST_RECOVERY_POSTGRES_URL`. The Postgres test
creates local tables and an `argus_app` test role; never point it at production.
