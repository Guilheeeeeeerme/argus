import unittest
from unittest.mock import Mock

try:
    import cv2
    import numpy as np
except ImportError:
    np = cv2 = None

from argus_edge_cv.pipeline import OpenCVVision
from argus_edge_cv.storage import FrameLoader


@unittest.skipIf(cv2 is None, "install edge-cv NumPy/OpenCV dependencies")
class VisionTests(unittest.TestCase):
    def test_synthetic_frames_motion_and_cosine_novelty(self):
        vision = OpenCVVision()
        a = np.zeros((64, 64, 3), dtype=np.uint8)
        b = a.copy()
        b[:, :32] = 255
        sig_a, sig_b = vision.signature(a), vision.signature(b)
        self.assertEqual(vision.motion(sig_a, sig_a), 0)
        self.assertGreater(vision.motion(sig_a, sig_b), 0.4)
        self.assertGreater(vision.novelty(sig_a, sig_b), 0.9)
        self.assertLess(abs(vision.novelty(sig_b, sig_b)), 0.00001)

    def test_s3_loader_enforces_tenant_scope_and_decodes(self):
        client = Mock()
        loader = FrameLoader(client, "frames")
        loader.identity = ("tenant", "site", "cam")
        for uri in (
            "https://evil/frame.jpg",
            "s3://other/tenant/site/cam/1.jpg",
            "s3://frames/foreign/site/cam/1.jpg",
        ):
            with self.assertRaises(ValueError):
                loader(uri)
        client.get_object.assert_not_called()
        _, jpeg = cv2.imencode(".jpg", np.zeros((16, 16, 3), dtype=np.uint8))
        body = Mock()
        body.read.return_value = jpeg.tobytes()
        client.get_object.return_value = {"Body": body}
        self.assertEqual(
            loader("s3://frames/tenant/site/cam/seq/1.jpg").shape, (16, 16, 3)
        )
        body.close.assert_called_once()

    def test_expired_object_is_permanent_but_service_failure_retries(self):
        class StorageError(Exception):
            def __init__(self, code):
                self.response = {"Error": {"Code": code}}

        client = Mock()
        loader = FrameLoader(client, "frames")
        loader.identity = ("tenant", "site", "cam")
        client.get_object.side_effect = StorageError("NoSuchKey")
        with self.assertRaises(ValueError):
            loader("s3://frames/tenant/site/cam/seq/1.jpg")
        client.get_object.side_effect = StorageError("ServiceUnavailable")
        with self.assertRaises(StorageError):
            loader("s3://frames/tenant/site/cam/seq/1.jpg")
