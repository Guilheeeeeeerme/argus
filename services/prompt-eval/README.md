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
