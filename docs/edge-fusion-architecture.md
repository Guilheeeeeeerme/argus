# Edge CV and sensor fusion

The optional `edge-cv` service runs beside the other services on the VPS, using
CPU inference. It is a service, not an on-prem device agent. go2rtc remains the
only media protocol translator; no vendor RTSP URL enters prompt-eval.
Production Compose and GHCR deployment remain owned by the sibling infra repo.
This change wires local Compose only. Production database migrations target the
existing Supabase `argus` schema through infra before application rollout.

## Architecture choices

| Decision | Selected approach | Alternatives and trade-offs |
| --- | --- | --- |
| Ingestion | go2rtc + Redis Streams; REST hooks as ingress | REST-only loses asynchronous fan-out; on-prem sidecars require a fleet and are deferred. |
| Edge inference | Sequential motion, YOLOv8n tracking, keyframe selection | Continuous CLIP memory is too expensive for CPU-first operation. |
| Duty cycle | Low-rate idle inference with motion/sensor-triggered bursts | Sensor-only gating can miss events when no sensor is present. |
| Gemini input | One ranked keyframe plus structural JSON | Collages sacrifice image detail; dual-stage VLM adds another service and is deferred. |
| Decision | Weighted consensus within prompt-eval | A separate decision microservice adds unnecessary state and deployment overhead. |

```text
Camera -> go2rtc -> stream-prep -> frames:ready -> edge-cv
                                  |                |
                                  |          candidates:ready
                                  |                |
                                  +----------> prompt-eval -> Gemini
                                    flag off        |
API /v1/hooks -> context:events -> fusion       consensus
                                                   |
                                        Detection + TriageCase
```

Existing Account, Unit, Camera, PromptSet, Detection, TriageCase and
WebhookEndpoint entities remain authoritative. Deprecated Decision, RuleSet and
Recipe entities are not reintroduced.

## Sensor contract and alignment

`POST /v1/hooks/{endpoint_id}` keeps bearer-token authentication and derives
account from the authenticated endpoint. Unit and camera are verified
within that tenant. Existing `kind`, `payload`, and optional camera scope remain.

New request/stream fields are `confidence` (optional finite number in [0,1]),
`role` (`trigger`, `filter`, or `context`, default `context`), and `occurred_at`
(timezone-aware timestamp, default ingestion time). Redis retains `received_at`,
`webhook_id`, and `context_event_id`. No database migration is required: the
extra fields are an ephemeral stream contract, not new ContextEvent columns.

`SensorFusionBuffer` is shared from `argus.services.sensor_fusion`. It correlates
by account AND unit, and by camera when the event has camera scope.
It matches inclusive ±5-second event-time windows and bounds retained event
count (10,000 by default). Malformed events are ignored. A sensor event cannot cross tenants even
when camera or unit strings coincide.

`stream-prep` adds each frame's `captured_at` to `preproc_meta.frames[]`; the
window-level `captured_at` remains the last frame's capture time. This additive
metadata avoids treating every frame in a window as captured simultaneously.
Fusion uses events already received when a window is processed; it does not
hold frames indefinitely for late webhook deliveries. Run one edge-cv replica: its
per-camera tracking and correlation state is local. On restart, it warms the
bounded sensor buffer from Redis history before processing frames. Horizontal
scaling requires partitioning by camera or shared correlation state.

## Edge cascade

1. Compute motion from frames, maintaining separate state per tenant/site/camera.
2. Run the detector during idle sampling or a motion/sensor-triggered burst.
3. Track allowlisted person, vehicle and bag detections; rank by confidence and
   remove similar keyframes using ResNet18 embedding cosine novelty. The embedding
   model loads only after a successful object detection.
4. Emit at most K=3 selected frame URIs with scores, tracks and aligned sensors.

The new `candidates:ready` stream preserves the original frame identity fields:
`account_id`, `unit_id`, `camera_id`, `sequence_id`, `captured_at`,
`frame_uris`, and `preproc_meta`. Additional fields are `edge_score`,
`motion_score`, `tracks`, `sensor_ids`, `sensors`, and `temporal_span_seconds`.
Lists and objects are JSON-encoded in Redis. Consumers use separate groups:
`edge-cv` for frames/context and `prompt-eval` for candidates/context.

The model runs on CPU by default. TensorRT is not a day-one dependency.
Detector tests use synthetic frames and an injected detector, without GPU or
model downloads. Enabled runtime downloads YOLOv8n and ResNet18 weights on
first use; mount/prewarm caches for offline operation.

## Consensus and VLM context

The enabled path selects one keyframe and adds screened, fenced JSON containing
`sensors`, `edge_tracks`, and `edge_score` to the existing grounding. Provider
routing, quotas, prompt fencing and structured-output validation remain active.

With normalized confidence values, the gate uses:

```text
score = 0.25 * sensor + 0.35 * edge + 0.40 * gemini
positive = score >= 0.55 OR (gemini.prompt_hit AND edge >= 0.40)
```

A `filter` with `payload.reject=true` or `payload.accepted=false` vetoes the candidate. Missing sensor evidence contributes
zero rather than being treated as confirmation. Invalid/nonfinite scores fail
closed. The existing negative discard still applies: consensus cannot create a
Detection without a valid positive prompt result. Rejected candidates create no
Detection, TriageCase or detections:positive message.

## Local operation and rollback

Copy `.env.example` to `.env`, then enable `EDGE_CV_ENABLED=true` and rebuild the
local services. Use Redis database /0 locally; production uses /1 in infra.

| Setting | Default | Meaning |
| --- | --- | --- |
| `EDGE_CV_ENABLED` | `false` | Select candidates path; false preserves legacy frames path. |
| `EDGE_IDLE_FPS` | `0.5` | Idle edge inference target. |
| `EDGE_BURST_FPS` | `3` | Burst inference target. |
| `EDGE_BURST_SECONDS` | `10` | Burst duration after a trigger. |
| `EDGE_MOTION_THRESHOLD` | `0.02` | Motion threshold. |
| `EDGE_MAX_KEYFRAMES` | `3` | Candidate keyframe cap. |
| `EDGE_SENSOR_WINDOW_SECONDS` | `5` | Symmetric correlation window. |

Edge inference cannot exceed frames supplied by stream-prep. The existing
`SAMPLE_FPS=1`, `WINDOW_SIZE=6` defaults are retained for rollback compatibility.
For three-frame-per-second bursts set `SAMPLE_FPS=3` or higher. stream-prep still
samples continuously and publishes windows, so this change saves detector/VLM
work rather than upstream camera bandwidth. Window batching also adds latency.

Stream delivery is at-least-once. A crash between publishing a candidate and
acknowledging its source can replay a sequence; the existing persistence path
does not enforce sequence uniqueness, so duplicate triage cases remain possible.
This slice does not introduce an exactly-once delivery contract.

Rollback: set `EDGE_CV_ENABLED=false` and recreate prompt-eval/edge-cv. The
prompt-eval frames consumer group remains independent of the edge group.

ONVIF Profile S/T cameras use their RTSP URL in Camera configuration. Operators
obtain it from the NVR or an ONVIF discovery tool; no discovery daemon is added.
go2rtc continues to abstract RTSP/RTMP/WebRTC/MJPEG.

## Token estimates

Illustrative image-token arithmetic from the design brief, not measured provider
billing (resolution/model affect actual usage):

| Input | Assumed image tokens | Additional text |
| --- | --- | --- |
| 30 seconds at 1 FPS | 30 × 258 = 7,740 | Prompt/context |
| Existing six-frame window | 6 × 258 = 1,548 | Prompt/context |
| One keyframe | 258 | Approximately 200–400 structural-context tokens |

Counting the proposed structural text, that is roughly 12–17× fewer tokens than
the raw image baseline and 2.4–3.4× fewer than the six-image baseline, excluding
shared prompt text. Image-only reduction is 30× and 6× respectively. Candidate
frequency and actual provider usage must be measured before claiming cost savings.
A 2–4-frame collage remains optional future work for spans over three seconds
without strong sensor context; the implemented primary path sends one frame.

## Exclusions

No MQTT bus, on-prem sidecar fleet, Agent entity, continuous CLIP bank, secondary
VLM service, production Auth0 change, or production rollout. Production wiring
requires a follow-up in infra after local validation.
