# Service sketch: stream-to-image

> Status: **NOT IMPLEMENTED** — handoff spec. Any agent should be able to
> start or resume from this document. Related: `docs/services/image-analysis.md`,
> `docs/realtime-page.md`, `docs/SPEC.md`.

## Purpose

Consume live camera streams (industry-standard RTSP/ONVIF config stored per
Camera) and break them down into **temporary images** (frame snapshots) that
downstream analysis consumes. This is the only service allowed to touch raw
media.

## Where it fits

```
Camera (rtsp url + creds, stored in ARGUS API)
   │
   ▼
stream-gateway (go2rtc; IMPLEMENTED as config-sync only, see below)
   │  restreams stable media endpoints
   ▼
stream-to-image (THIS SERVICE — not implemented)
   │  samples frames → temporary images in MinIO (TTL)
   ▼
Redis stream `ingest:sequences` (existing contract, see image-analysis.md)
```

## What exists today

| Piece | State |
|---|---|
| `cameras.stream_url/stream_username/stream_password` | Implemented (`locations`/`cameras` tables, admin UI on Location plan) |
| `GET /v1/internal/stream-configs` (X-Stream-Gateway-Token) | Implemented in `apps/api/src/argus/api/internal.py` — returns all active cameras + stream config |
| `services/stream-gateway` (go2rtc + config sync) | **To build** — see "Gateway sketch" |
| Frame sampling → temporary images | **To build** — this service |

## Responsibilities (to build)

1. **Connect** to each camera stream via the stream-gateway's normalized
   endpoint (go2rtc `rtsp://stream-gateway:8554/{camera_id}` style), never the
   vendor URL directly.
2. **Sample** frames on motion/edge triggers or fixed cadence
   (configurable per camera: `fps` or trigger mode).
3. **Store** sampled frames as temporary images in MinIO under
   `{company_id}/{camera_id}/{ingestion_id}/{frame_n}.jpg`.
   - Apply a TTL (lifecycle rule) so frames are ephemeral — "temporary images".
   - Presigned GET URLs for downstream analyzers (they never get credentials).
4. **Emit** an ingest message per suspicious sequence to Redis stream
   `ingest:sequences` (contract in `docs/services/image-analysis.md`), carrying
   `frame_uris`, `company_id`, `camera_id`, `location_id`, `captured_at`,
   `edge_trigger_metadata`.
5. **Cleanup** — rely on MinIO lifecycle rules; never keep frames beyond TTL.

## Gateway sketch (go2rtc wrapper)

- Compose service `stream-gateway` (image `alexxit/go2rtc`) + a small
  `config-sync` sidecar (python:slim) that every N seconds:
  1. `GET /v1/internal/stream-configs` with `X-Stream-Gateway-Token`
     (`STREAM_GATEWAY_TOKEN` env, exists in `argus.config`).
  2. Renders go2rtc `streams:` YAML: each camera as
     `{camera_id}: rtsp://{user}:{pass}@{host}/{path}` (or ONVIF profile later).
  3. Writes the shared volume config; go2rtc hot-reloads via its API
     (`PUT /api/streams/{name}`).
- ARGUS app never receives media traffic; only the config is stored.

## Configuration (env)

| Var | Meaning |
|---|---|
| `STREAM_GATEWAY_TOKEN` | shared secret for the internal route |
| `MINIO_*` / `S3_*` | frame bucket + presigning (existing settings) |
| `REDIS_URL` | ingest stream target |
| `FRAME_TTL_HOURS` | MinIO lifecycle hint (default 24h) |
| `SAMPLE_FPS` / `TRIGGER_MODE` | sampling policy per camera |

## Runbook (start / resume)

1. Fresh clone → `./scripts/up.sh -d` (API + Postgres + Redis + MinIO up).
2. Cameras configured with `stream_url` via Admin → Location → Plan.
3. Implement this service as `services/stream-to-image/` (suggest: Python +
   ffmpeg, or Go + gocv; both fine — keep it stateless, concurrency via
   per-camera tasks).
4. Register in `docker-compose.yml` on network `argus_dmz`; depends on
   `stream-gateway` + `redis` + `minio`.
5. Acceptance: frames appear in the bucket with TTL; messages land on
   `ingest:sequences`; `redis-cli XLEN ingest:sequences` grows; killed service
   resumes sampling without duplicating `ingestion_id`s (idempotency per
   `ingestion_id`, existing unique constraint on evidences).

## Open decisions

- Trigger mode default (motion vs fixed fps) and whether the edge Agent does
  pre-filtering (the current ingest flow already assumes edge-side filtering).
- go2rtc vs mediamtx for the gateway.
- Whether sampling runs at the Agent instead (edge) — current architecture
  says yes; this service may become a fallback for agentless cameras (e.g.
  direct RTSP). Decide before implementing.
