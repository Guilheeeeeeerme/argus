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
- Camera + establishment + company identity from gateway naming / API sync
  (same ids the API stores).

## Outputs

### Object storage (MinIO)

- Temporary frame objects under a tenant/camera/sequence key layout.
- **TTL / lifecycle** so frames are ephemeral (“temporary images”).
- Downstream services receive URIs (presigned GET as needed); they never get
  MinIO credentials from this path.

### Redis stream `frames:ready`

| Field | Type / notes |
|-------|----------------|
| `company_id` | UUID |
| `establishment_id` | UUID |
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

## Non-responsibilities

- VLM calls, prompt evaluation, detection persistence (prompt-eval).
- Triage / WebSocket fan-out (API).
- Drawing sketches, ROI, or rule schedules (out of MVP).

## Module map

| Concern | Module |
|---------|--------|
| Media preprocessing | `argus_stream_prep.preprocessing` |
| Temporal windowing | `temporal_window` |
