"""Optional real CPU library checks; no pretrained downloads or GPU required."""

import importlib.util
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch


@unittest.skipUnless(
    importlib.util.find_spec("ultralytics"), "requires container vision runtime"
)
class RuntimeTests(unittest.TestCase):
    def test_real_bytetrack_with_mock_detection_boxes(self):
        import numpy as np
        from argus_edge_cv.detector import YOLODetector
        from ultralytics.engine.results import Boxes

        detector = YOLODetector()
        detector.model = Mock()
        detector.model.predict.return_value = [
            SimpleNamespace(
                boxes=Boxes(
                    np.array([[0, 0, 32, 32, 0.9, 0]], dtype=np.float32),
                    orig_shape=(64, 64),
                ),
                names={0: "person"},
            )
        ]
        tracks = detector.detect(np.zeros((64, 64, 3), dtype=np.uint8), ("a", "b", "c"))
        self.assertEqual(tracks[0]["class_name"], "person")
        self.assertEqual(tracks[0]["bbox"], [0, 0, 32, 32])

    def test_real_resnet_transform_and_cpu_embedding_without_download(self):
        import numpy as np
        from argus_edge_cv.detector import ResNetEmbedder
        from torchvision.models import resnet18

        with patch(
            "torchvision.models.resnet18",
            side_effect=lambda **kw: resnet18(weights=None),
        ):
            vector = ResNetEmbedder()(np.zeros((64, 64, 3), dtype=np.uint8))
        self.assertEqual(vector.shape, (512,))
        self.assertTrue(np.isfinite(vector).all())

    def test_historical_one_frame_uses_fresh_tracker(self):
        import json

        import numpy as np
        from argus_edge_cv.detector import YOLODetector
        from argus_edge_cv.pipeline import EdgeInferencePipeline, Settings
        from ultralytics.engine.results import Boxes

        def result(x):
            return [
                SimpleNamespace(
                    boxes=Boxes(
                        np.array([[x, x, x + 10, x + 10, 0.9, 0]], dtype=np.float32),
                        orig_shape=(64, 64),
                    ),
                    names={0: "person"},
                )
            ]

        detector = YOLODetector()
        detector.model = Mock()
        detector.model.predict.side_effect = [result(0), result(40), result(40)]
        pipeline = EdgeInferencePipeline(
            Settings(), detector, lambda uri: np.zeros((64, 64, 3), dtype=np.uint8)
        )
        fields = {
            "company_id": "a",
            "establishment_id": "b",
            "camera_id": "c",
            "sequence_id": "new",
            "captured_at": "2026-10-01T12:01:00+00:00",
            "frame_uris": json.dumps(["uri"]),
        }
        self.assertIsNotNone(pipeline.process(fields))
        fields.update(sequence_id="old", captured_at="2026-10-01T12:00:00+00:00")
        self.assertIsNotNone(pipeline.process(fields))
        self.assertIsNotNone(pipeline.process(fields))
