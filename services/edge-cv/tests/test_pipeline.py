import json
import unittest

from argus_edge_cv.pipeline import EdgeInferencePipeline, Settings


class Vision:
    def signature(self, frame):
        return frame

    def motion(self, old, new):
        return 1.0 if old != new else 0.0

    def novelty(self, old, new):
        return 1.0 if old != new else 0.0


class Detector:
    def __init__(self):
        self.calls = []

    def detect(self, frame, identity):
        self.calls.append(identity)
        return [
            {
                "track_id": 1,
                "class_name": "person",
                "confidence": frame / 10,
                "bbox": [0, 0, 5, 5],
            }
        ]


def fields(company="a"):
    return {
        "company_id": company,
        "establishment_id": "b",
        "camera_id": "c",
        "sequence_id": "seq",
        "captured_at": "2026-10-01T12:00:00+00:00",
        "frame_uris": json.dumps(["1", "2", "3", "4"]),
        "preproc_meta": json.dumps({"sample_interval_seconds": 1}),
    }


class PipelineTests(unittest.TestCase):
    def pipeline(self):
        self.detector = Detector()
        return EdgeInferencePipeline(Settings(), self.detector, int, vision=Vision())

    def test_confidence_ranking_and_cap(self):
        result = self.pipeline().process(fields())
        self.assertEqual(json.loads(result["frame_uris"]), ["4", "3", "2"])
        self.assertEqual(float(result["edge_score"]), 0.4)
        self.assertEqual(result["sequence_id"], "seq")

    def test_idle_skips_static_detector_and_trigger_wakes_it(self):
        pipeline = self.pipeline()
        message = fields()
        message["frame_uris"] = '["1", "1"]'
        pipeline.process(message)
        self.assertEqual(len(self.detector.calls), 1)
        message["captured_at"] = "2026-10-01T12:01:00+00:00"
        pipeline.process(message, sensors=[{"role": "trigger", "id": "s"}])
        self.assertGreater(len(self.detector.calls), 1)

    def test_tenant_state_is_separate(self):
        pipeline = self.pipeline()
        pipeline.process(fields("a"))
        result = pipeline.process(fields("other"))
        self.assertIsNotNone(result)
        self.assertIn(("other", "b", "c"), self.detector.calls)

    def test_malformed_and_nonfinite_fields_rejected(self):
        pipeline = self.pipeline()
        for change in (
            {"frame_uris": "{}"},
            {"captured_at": "bad"},
            {"company_id": ""},
            {"preproc_meta": '{"sample_interval_seconds": NaN}'},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                pipeline.process(fields() | change)

    def test_publish_retry_reuses_candidate_without_reprocessing(self):
        from argus_edge_cv.worker import Worker

        class Redis:
            def __init__(self):
                self.acks = []
                self.published = []
                self.fail = True

            def xadd(self, stream, payload, **kw):
                if self.fail:
                    self.fail = False
                    raise ConnectionError()
                self.published.append(payload)

            def xack(self, *args):
                self.acks.append(args)

        redis = Redis()
        worker = Worker(redis, self.pipeline(), sensors=None)
        with self.assertRaises(ConnectionError):
            worker.handle("frames:ready", "1-0", fields())
        calls = len(self.detector.calls)
        worker.handle("frames:ready", "1-0", fields())
        self.assertEqual(len(self.detector.calls), calls)
        self.assertEqual(len(redis.published), 1)
        self.assertEqual(len(redis.acks), 1)

    def test_sensors_only_from_retained_keyframes(self):
        from datetime import datetime

        class Buffer:
            def match(self, **kwargs):
                return [
                    {"id": str(int(kwargs["timestamp"].timestamp())), "role": "context"}
                ]

        pipeline = EdgeInferencePipeline(
            Settings(max_keyframes=1), Detector(), int, vision=Vision()
        )
        result = pipeline.process(fields(), sensor_buffer=Buffer())
        expected = str(int(datetime.fromisoformat(fields()["captured_at"]).timestamp()))
        self.assertEqual(json.loads(result["sensor_ids"]), [expected])

    def test_malformed_message_acked_without_publish(self):
        from unittest.mock import Mock

        from argus_edge_cv.worker import Worker

        redis = Mock()
        Worker(redis, self.pipeline(), None).handle("frames:ready", "bad-id", {})
        redis.xack.assert_called_once_with("frames:ready", "edge-cv", "bad-id")
        redis.xadd.assert_not_called()

    def test_ack_retry_does_not_republish(self):
        from unittest.mock import Mock

        from argus_edge_cv.worker import Worker

        redis = Mock()
        redis.xack.side_effect = [ConnectionError(), 1]
        worker = Worker(redis, self.pipeline(), None)
        with self.assertRaises(ConnectionError):
            worker.handle("frames:ready", "id", fields())
        worker.handle("frames:ready", "id", fields())
        redis.xadd.assert_called_once()

    def test_semantic_embedding_runs_only_after_detection(self):
        from unittest.mock import Mock

        embedder = Mock(side_effect=lambda frame: frame)
        pipeline = EdgeInferencePipeline(
            Settings(), Detector(), int, vision=Vision(), embedder=embedder
        )
        message = fields() | {"frame_uris": '["1", "1"]'}
        pipeline.process(message)
        embedder.assert_called_once_with(1)

    def test_selected_metadata_matches_ranked_uris(self):
        message = fields()
        message["preproc_meta"] = json.dumps(
            {
                "frames": [
                    {"captured_at": f"2026-10-01T11:59:5{i}+00:00", "index": i}
                    for i in range(4)
                ]
            }
        )
        result = self.pipeline().process(message)
        metadata = json.loads(result["preproc_meta"])["frames"]
        self.assertEqual([m["index"] for m in metadata], [3, 2, 1])
        self.assertEqual(metadata[0]["captured_at"], "2026-10-01T11:59:53+00:00")

    def test_custom_stream_contract(self):
        from unittest.mock import Mock

        from argus_edge_cv.worker import Worker

        redis = Mock()
        worker = Worker(
            redis,
            self.pipeline(),
            None,
            frames_stream="f",
            context_stream="s",
            candidates_stream="c",
            frames_group="fg",
            context_group="sg",
        )
        worker.handle("f", "id", fields())
        self.assertEqual(redis.xadd.call_args.args[0], "c")
        redis.xack.assert_called_once_with("f", "fg", "id")

    def test_disabled_entrypoint_imports_no_heavy_libraries(self):
        import os
        import subprocess
        import sys

        code = """
import sys
from unittest.mock import patch, Mock
from argus_edge_cv.__main__ import main
with patch("threading.Event", return_value=Mock()), patch("signal.signal"):
    main()
assert not any(m in sys.modules for m in ("torch", "cv2", "ultralytics", "redis", "boto3"))
"""
        subprocess.run(
            [sys.executable, "-c", code],
            env=os.environ | {"EDGE_CV_ENABLED": "false"},
            check=True,
        )

    def test_older_failed_window_is_not_lost_after_newer_success(self):
        from unittest.mock import Mock

        from argus_edge_cv.worker import Worker

        loader = Mock(side_effect=[ConnectionError()] + [1, 2, 3, 4] * 2)
        pipeline = EdgeInferencePipeline(
            Settings(), Detector(), loader, vision=Vision()
        )
        redis = Mock()
        worker = Worker(redis, pipeline, None)
        with self.assertRaises(ConnectionError):
            worker.handle("frames:ready", "old", fields())
        newer = fields() | {"captured_at": "2026-10-01T12:01:00+00:00"}
        worker.handle("frames:ready", "new", newer)
        last = pipeline.states[("a", "b", "c")]["last_time"]
        worker.handle("frames:ready", "old", fields())
        self.assertEqual(redis.xadd.call_count, 2)
        self.assertEqual(pipeline.states[("a", "b", "c")]["last_time"], last)
