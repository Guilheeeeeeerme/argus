# Edge CV (CPU)

Optional single-replica consumer: frames:ready + context:events → candidates:ready.
Both consumer groups are edge-cv. EDGE_CV_ENABLED defaults false: the process
waits for shutdown without importing Redis, NumPy, OpenCV, Torch or Ultralytics.

Enabled processing uses OpenCV grayscale frame difference, CPU YOLOv8n with
ByteTrack isolated by company/establishment/camera, then ResNet18 embedding cosine novelty and confidence ranking. ResNet loads only
after object detection, runs on CPU and never acts as a continuous memory bank.
TensorRT is not loaded. Torch 2.5.1 and torchvision 0.20.1 are paired in the image.
The YOLO checkpoint defaults to yolov8n.pt (Ultralytics downloads it on first use);
provide EDGE_YOLO_MODEL pointing to a mounted checkpoint for offline startup.
ResNet18 pretrained weights also download on first eligible detection; prewarm or
mount the Torch checkpoint cache for offline use.

Defaults: EDGE_IDLE_FPS=0.5, EDGE_BURST_FPS=3, EDGE_BURST_SECONDS=10,
EDGE_MOTION_THRESHOLD=0.02, EDGE_NOVELTY_THRESHOLD=0.05,
EDGE_MAX_KEYFRAMES=3 (maximum 3), EDGE_SENSOR_WINDOW_SECONDS=5.
EDGE_CLASSES is a comma-separated class allowlist. EDGE_TENSORRT_ENABLED must
remain false. S3_* and REDIS_URL use the same conventions as stream-prep.

Motion or a matched role=trigger sensor opens the burst sampling interval.
Processing consumes prepared windows, so rates cannot exceed upstream sampling:
set stream-prep SAMPLE_FPS to at least EDGE_BURST_FPS for a 3 FPS supply. Window
batching adds latency; this worker does not reconfigure go2rtc or stream-prep.
Frame metadata captured_at gives exact per-frame time; legacy windows infer
sample times backwards from their captured_at endpoint at the supplied
sample_interval_seconds (default 1). Matching uses only already-arrived sensors;
future arrivals are not retroactively joined. Recent sensor history is replayed
on startup. Keep one replica: consumer-group partitioning across multiple workers
would separate sensor and camera state.

Candidate frames are ranked by confidence and capped at K; sensors only accompany
retained keyframes. Identity, sequence_id, captured_at and preproc_meta are retained.
Additional fields: edge_score, motion_score, tracks, sensors, sensor_ids,
temporal_span_seconds. Selected frame metadata follows the selected URI order. Lists/objects are JSON Redis strings.
Storage reads require the configured bucket and exact tenant/site/camera prefix.
No frame, prompt or sensor payloads are logged.

Malformed messages and expired/missing frame objects are acknowledged without publication.
Older reclaimed windows use isolated sampling and tracker state without rewinding newer windows. Track IDs on replay belong to that temporary session. Transient errors leave
entries pending and reclaim after 30 seconds. In-process publication/ACK retries
reuse cached output. Delivery is at-least-once: a crash after XADD but before ACK
can duplicate a sequence; downstream must deduplicate sequence_id. Camera state
is bounded to 256 identities. Sensor history is bounded to 10,000 events.

Run CPU unit tests (mocked detector, no GPU/model download):

```sh
PYTHONPATH=services/edge-cv/src:apps/api/src python -m unittest discover -s services/edge-cv/tests
```

Synthetic image/storage tests require NumPy and OpenCV. Two optional container
runtime tests exercise actual ByteTrack and ResNet CPU APIs with mocked/random
weights; they require installed vision dependencies but never download models.
