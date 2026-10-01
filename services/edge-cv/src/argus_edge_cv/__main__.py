import logging
import os
import signal
import socket
import threading


def main():
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    if os.getenv("EDGE_CV_ENABLED", "false").lower() not in ("1", "true", "yes"):
        logging.getLogger(__name__).info("edge-cv disabled")
        stop.wait()
        return
    if os.getenv("EDGE_TENSORRT_ENABLED", "false").lower() in ("1", "true", "yes"):
        raise ValueError("TensorRT is not supported by the CPU worker")
    import boto3
    import redis
    from argus.services.sensor_fusion import SensorFusionBuffer

    from .detector import ResNetEmbedder, YOLODetector
    from .pipeline import EdgeInferencePipeline, Settings
    from .storage import FrameLoader
    from .worker import Worker, consume

    settings = Settings(
        idle_fps=float(os.getenv("EDGE_IDLE_FPS", ".5")),
        burst_fps=float(os.getenv("EDGE_BURST_FPS", "3")),
        burst_seconds=float(os.getenv("EDGE_BURST_SECONDS", "10")),
        motion_threshold=float(os.getenv("EDGE_MOTION_THRESHOLD", ".02")),
        novelty_threshold=float(os.getenv("EDGE_NOVELTY_THRESHOLD", ".05")),
        max_keyframes=int(os.getenv("EDGE_MAX_KEYFRAMES", "3")),
    )
    client = boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL", "http://minio:9000"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID", "minioadmin"),
        aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY", "minioadmin"),
        region_name=os.getenv("S3_REGION", "us-east-1"),
    )
    loader = FrameLoader(client, os.getenv("S3_BUCKET_NAME", "argus-frames"))
    detector = YOLODetector(
        os.getenv("EDGE_YOLO_MODEL", "yolov8n.pt"),
        classes=os.getenv(
            "EDGE_CLASSES",
            "person,bicycle,car,motorcycle,bus,truck,backpack,handbag,suitcase",
        ).split(","),
    )
    pipeline = EdgeInferencePipeline(
        settings, detector, loader, embedder=ResNetEmbedder()
    )
    conn = redis.Redis.from_url(
        os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True
    )
    sensors = SensorFusionBuffer(
        window_seconds=float(os.getenv("EDGE_SENSOR_WINDOW_SECONDS", "5"))
    )
    try:
        worker = Worker(
            conn,
            pipeline,
            sensors,
            frames_stream=os.getenv("FRAMES_READY_STREAM", "frames:ready"),
            context_stream=os.getenv("CONTEXT_EVENTS_STREAM", "context:events"),
            candidates_stream=os.getenv("CANDIDATES_READY_STREAM", "candidates:ready"),
            frames_group=os.getenv("FRAMES_READY_GROUP", "edge-cv"),
            context_group=os.getenv("CONTEXT_EVENTS_GROUP", "edge-cv"),
        )
        consume(conn, worker, stop, socket.gethostname())
    finally:
        conn.close()
        client.close()


if __name__ == "__main__":
    main()
