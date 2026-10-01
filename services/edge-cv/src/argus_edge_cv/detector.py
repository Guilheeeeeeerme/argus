"""Shared CPU YOLOv8n model and isolated per-camera ByteTrack state."""

from collections import OrderedDict
from types import SimpleNamespace


class YOLODetector:
    def __init__(self, model_path="yolov8n.pt", classes=None, max_cameras=256):
        self.model_path = model_path
        self.classes = set(
            classes
            or (
                "person",
                "bicycle",
                "car",
                "motorcycle",
                "bus",
                "truck",
                "backpack",
                "handbag",
                "suitcase",
            )
        )
        self.max_cameras = max_cameras
        self.model = None
        self.trackers = OrderedDict()

    def detect(self, frame, identity):
        from ultralytics import YOLO
        from ultralytics.trackers.byte_tracker import BYTETracker

        if self.model is None:
            self.model = YOLO(self.model_path)
        result = self.model.predict(frame, device="cpu", verbose=False)[0]
        if identity not in self.trackers:
            self.trackers[identity] = BYTETracker(
                SimpleNamespace(
                    track_high_thresh=0.25,
                    track_low_thresh=0.1,
                    new_track_thresh=0.25,
                    track_buffer=30,
                    match_thresh=0.8,
                    fuse_score=True,
                ),
            )
        self.trackers.move_to_end(identity)
        while len(self.trackers) > self.max_cameras:
            self.trackers.popitem(last=False)
        tracks = self.trackers[identity].update(result.boxes.cpu().numpy(), frame)
        return [
            {
                "track_id": int(t[4]),
                "class_name": result.names[int(t[6])],
                "confidence": float(t[5]),
                "bbox": [float(v) for v in t[:4]],
            }
            for t in tracks
            if result.names[int(t[6])] in self.classes
        ]


class ResNetEmbedder:
    """Semantic keyframe descriptor, loaded only after the first object detection."""

    def __init__(self):
        self.model = None
        self.transform = None

    def __call__(self, frame):
        import torch
        from torchvision.models import ResNet18_Weights, resnet18

        if self.model is None:
            weights = ResNet18_Weights.DEFAULT
            backbone = resnet18(weights=weights)
            self.model = (
                torch.nn.Sequential(*list(backbone.children())[:-1]).eval().cpu()
            )
            self.transform = weights.transforms()
        rgb = torch.from_numpy(frame[:, :, ::-1].copy()).permute(2, 0, 1)
        with torch.inference_mode():
            vector = self.model(self.transform(rgb).unsqueeze(0)).flatten()
        return vector.numpy()
