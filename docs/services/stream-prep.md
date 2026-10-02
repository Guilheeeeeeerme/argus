# Service: stream-prep

Handoff spec for the MVP media preprocessing service. Related:
`docs/SPEC.md`, `docs/ai-engineering.md`, `docs/services/prompt-eval.md`.

## Purpose

Consume restreamed camera media from **stream-gateway** (go2rtc), sample and
preprocess frames, store ephemeral images in MinIO with a TTL, and publish
ready sequences for **prompt-eval**.

This is the only service that should touch raw live media after the gateway.

## Where it fits

```
Camera (RTSP config in API)
   │
   ▼
stream-gateway (go2rtc)
   │  rtsp://stream-gateway:8554/{camera_id}
   ▼
stream-prep (THIS SERVICE)
   │  sample + preprocess → MinIO (TTL)
   │  Redis stream: frames:ready
   ▼
prompt-eval
```

## Inputs

- Stable media endpoints from **go2rtc** / stream-gateway (never vendor RTSP
  URLs directly).
- Camera + unit + account identity from gateway naming / API sync
  (same ids the API stores).

## Outputs

### Object storage (MinIO)

- Temporary frame objects under a tenant/camera/sequence key layout.
- **TTL / lifecycle** so frames are ephemeral (“temporary images”).
- Downstream services receive URIs (presigned GET as needed); they never get
  MinIO credentials from this path.

### Latest frame per camera (triage grid)

Every sampled frame is also written to a **stable** key
`{account}/{unit}/{camera}/latest.jpg` (`Cache-Control: no-store`,
metadata `captured-at`) and pointed to from the Redis hash
`frame:latest:{camera_id}`:

| Field | Notes |
|-------|-------|
| `uri` | `s3://bucket/{account}/{unit}/{camera}/latest.jpg` |
| `captured_at` | ISO-8601 (UTC) of the sample |
| `account_id` / `unit_id` | Same ids as `frames:ready` |

The hash expires after `LATEST_FRAME_TTL` seconds (default 30), so a camera
whose stream stopped drops out of the grid as "Sem sinal". The API serves the
bytes through `GET /v1/accounts/{c}/cameras/{cam}/latest-frame` (ETag =
`captured_at`); the browser never talks to MinIO or go2rtc. Set
`LATEST_FRAME_ENABLED=false` to skip it. Failures are logged and never block
the `frames:ready` pipeline. Cost: one extra PUT per camera per sample.

### Redis stream `frames:ready`

| Field | Type / notes |
|-------|----------------|
| `account_id` | UUID |
| `unit_id` | UUID |
| `camera_id` | UUID |
| `sequence_id` | UUID / opaque sequence id |
| `captured_at` | ISO-8601 timestamp |
| `frame_uris[]` | List of object URIs |
| `preproc_meta` | JSON from `argus_stream_prep.preprocessing` |

## Responsibilities

1. **Connect** to each active camera via stream-gateway.
2. **Sample** frames (cadence / trigger policy per camera as configured).
3. **Preprocess** via `argus_stream_prep.preprocessing` (normalize, enrich;
   record `preproc_meta`).
4. **Window** frames into sequences (`temporal_window`).
5. **Store** frames in MinIO with TTL.
6. **Publish** one `frames:ready` message per sequence.
7. **Point** `frame:latest:{camera_id}` at the newest `latest.jpg` (best effort).

## Non-responsibilities

- VLM calls, prompt evaluation, detection persistence (prompt-eval).
- Triage / WebSocket fan-out (API).
- Drawing sketches, ROI, or rule schedules (out of MVP).

## Module map

| Concern | Module |
|---------|--------|
| Media preprocessing | `argus_stream_prep.preprocessing` |
| Temporal windowing | `temporal_window` |
