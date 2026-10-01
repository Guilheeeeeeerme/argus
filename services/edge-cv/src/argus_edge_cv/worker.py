"""Redis delivery: publish before ACK; malformed entries are acknowledged safely."""

import json
import logging

logger = logging.getLogger(__name__)
GROUP = "edge-cv"
FRAMES = "frames:ready"
CONTEXT = "context:events"


class Worker:
    def __init__(
        self,
        redis,
        pipeline,
        sensors,
        *,
        frames_stream=FRAMES,
        context_stream=CONTEXT,
        candidates_stream="candidates:ready",
        frames_group=GROUP,
        context_group=GROUP,
    ):
        self.redis, self.pipeline, self.sensors = redis, pipeline, sensors
        self.frames_stream, self.context_stream = frames_stream, context_stream
        self.candidates_stream = candidates_stream
        self.groups = {frames_stream: frames_group, context_stream: context_group}
        self.pending = {}

    def handle(self, stream, message_id, fields):
        key = (stream, message_id)
        if key not in self.pending:
            try:
                if stream == self.context_stream:
                    event = dict(fields)
                    event["payload"] = json.loads(event.get("payload", "{}"))
                    self.sensors.add(event)
                    candidate = None
                else:
                    loader = self.pipeline.load_frame
                    if hasattr(loader, "identity"):
                        loader.identity = tuple(
                            fields[k]
                            for k in ("company_id", "establishment_id", "camera_id")
                        )
                    candidate = self.pipeline.process(
                        fields, sensor_buffer=self.sensors
                    )
            except (ValueError, KeyError, TypeError):
                logger.warning("malformed entry stream=%s id=%s", stream, message_id)
                candidate = None
            self.pending[key] = candidate
        candidate = self.pending[key]
        # Keep cached output until ACK succeeds: retry cannot lose a sampled candidate.
        if candidate is not None:
            self.redis.xadd(
                self.candidates_stream, candidate, maxlen=10000, approximate=True
            )
            self.pending[key] = None
        self.redis.xack(stream, self.groups[stream], message_id)
        del self.pending[key]


def consume(redis, worker, stop, consumer):
    from redis.exceptions import ResponseError

    streams = (worker.context_stream, worker.frames_stream)
    for stream in streams:
        try:
            redis.xgroup_create(stream, worker.groups[stream], id="0", mkstream=True)
        except ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
    cursors = {stream: "0-0" for stream in streams}
    # Single replica: rebuild the bounded buffer after restarts before processing frames.
    for _, fields in reversed(redis.xrevrange(worker.context_stream, count=10000)):
        try:
            event = dict(fields)
            event["payload"] = json.loads(event.get("payload", "{}"))
            worker.sensors.add(event)
        except (ValueError, TypeError):
            continue
    while not stop.is_set():
        try:
            # Backpressure: finish cached deliveries before accepting more work.
            for stream, message_id in list(worker.pending):
                try:
                    worker.handle(stream, message_id, {})
                except Exception:  # noqa: BLE001 - transient IO/model failures remain pending; never log payloads
                    logger.warning(
                        "delivery deferred stream=%s id=%s", stream, message_id
                    )
            if worker.pending:
                stop.wait(1)
                continue
            # Reclaim abandoned deliveries as well as retrying this worker failures.
            for stream in streams:
                claimed = redis.xautoclaim(
                    stream,
                    worker.groups[stream],
                    consumer,
                    min_idle_time=30000,
                    start_id=cursors[stream],
                    count=10,
                )
                cursors[stream] = claimed[0]
                for message_id, fields in claimed[1]:
                    try:
                        worker.handle(stream, message_id, fields)
                    except Exception:  # noqa: BLE001 - transient IO/model failures remain pending; never log payloads
                        logger.warning(
                            "retry pending stream=%s id=%s", stream, message_id
                        )
            batches = []
            for group in dict.fromkeys(worker.groups.values()):
                group_streams = {
                    stream: ">" for stream in streams if worker.groups[stream] == group
                }
                batches.extend(
                    redis.xreadgroup(
                        group, consumer, group_streams, count=10, block=1000
                    )
                )
            for stream, entries in sorted(
                batches, key=lambda item: item[0] != worker.context_stream
            ):
                for message_id, fields in entries:
                    try:
                        worker.handle(stream, message_id, fields)
                    except Exception:  # noqa: BLE001 - transient IO/model failures remain pending; never log payloads
                        logger.warning(
                            "processing deferred stream=%s id=%s", stream, message_id
                        )
        except Exception:  # noqa: BLE001 - transient IO/model failures remain pending; never log payloads
            logger.warning("redis unavailable; retrying")
            stop.wait(1)
