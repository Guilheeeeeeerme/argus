# Service sketch: image-analysis (detection over rules)

> Status: **IMPLEMENTED inside `apps/api` worker** (`vlm_analyzer` Celery task +
> `recipe_builder` + `openai_vlm`), to be extracted into a standalone
> microservice when load demands it. This document is the handoff: any agent
> can resume/extract using it. Related: `stream-to-image.md`,
> `decision-engine.md`, `docs/SPEC.md`.

## Purpose

Turn temporary frame images into **Detections** — `{ detection_class,
confidence, description }` — analyzed **over the rules** (Recipe prompt +
Rule bindings), producing Evidence rows that feed the decision engine.

## Pipeline (current, working)

```
Redis stream ingest:sequences (consumer group `vlm-analyzers`)
  → vlm_analyzer.process_ingest_stream (Celery beat, every 2s, batch ≤10)
    → analyze_ingest_message (per message, autoretry 3x → DLQ)
        1. load Recipe (latest version) for the message rule_set_id
        2. load Rules bound to that rule set
        3. RAG: retrieve false-positive feedback for this camera (pgvector)
        4. build_prompt(recipe, rules, rag) → VLM system prompt
        5. VLM analyze(frame_uris, output_schema) → structured JSON
        6. compute_severity_score(vlm_result, rules):
             rule matches when
               - rule.detection_class is null OR == vlm_result.detection_class
               - vlm confidence >= rule.confidence_threshold
               - rule.condition matches (field/op/value)
             → sum of matched severity weights (+ fallback hint)
        7. Evidence row: vlm_result, detection_class, confidence,
           severity_score, frame_storage_uri
  → aggregate_evidence.delay(evidence_id)  (see decision-engine.md)
```

## Key contracts

- **Stream fields** (`ingest:sequences`): `company_id`, `camera_id`,
  `rule_set_id`, `ingestion_id` (idempotency key), `region_id?`,
  `captured_at`, `frame_uris` (JSON), `edge_trigger_metadata` (JSON).
  Consumer group: `vlm-analyzers` (created by
  `apps/api/scripts/init_redis_streams.py`).
- **Recipe output schema** (seeded example): `is_suspicious`,
  `detection_class` (enum), `confidence_score` (0..1), `description`.
- **Rule binding columns**: `rules.detection_class`, `rules.confidence_threshold`
  (default 0.500). `Evidence.detection_class`, `Evidence.confidence` are the
  extracted values.
- **DLQ**: failed messages land on `ingest:dlq` with `error` after 3 retries.

## Where the code lives

| Concern | File |
|---|---|
| Celery task + stream consumer | `apps/api/src/argus/workers/vlm_analyzer.py` |
| Prompt building + severity/binding | `apps/api/src/argus/services/recipe_builder.py` |
| VLM clients (OpenAI + Mock) | `apps/api/src/argus/integrations/openai_vlm.py` |
| RAG feedback retrieval | `recipe_builder.retrieve_rag_feedback` (pgvector cosine) |
| Rule/region models | `apps/api/src/argus/domain/models/__init__.py` |

## Extraction checklist (when to split into its own service)

1. Move `vlm_analyzer` + `recipe_builder` + `openai_vlm` into
   `services/image-analysis/` with its own Celery app (same Redis broker).
2. Keep the stream contract identical — zero API changes needed.
3. Config it needs: `REDIS_URL`, `DATABASE_URL`, `OPENAI_API_KEY`,
   `AUTH0_USE_MOCK` (mock client), MinIO creds (frame reads).
4. Register in compose as `analysis` on `argus_dmz`; remove the task routes
   from the api worker's celery include list.
5. Acceptance: same severity outputs for the seeded fixtures; DLQ behavior
   unchanged; scale-out = plain `celery worker -c N`.

## Runbook (start / resume)

- Runs inside the `worker` compose service today:
  `docker compose up -d worker` — Celery beat polls `ingest:sequences`.
- Manual re-run of a DLQ'd message: inspect `ingest:dlq` (XRANGE), fix the
  cause, XADD back to `ingest:sequences` with the same `ingestion_id`
  (unique constraint prevents duplicate Evidence rows).
- Tests: `apps/api/tests/test_workers.py::test_vlm_analyze_creates_evidence`,
  `test_lens_builder.py` (recipe binding tests).

## Open decisions

- Real detection-class taxonomy: enum per company vs global registry.
- Confidence calibration from VLM tokens/logprobs (today it trusts the model's
  self-reported score).
- Multiple detections per frame (current schema assumes one class per
  sequence analysis).
