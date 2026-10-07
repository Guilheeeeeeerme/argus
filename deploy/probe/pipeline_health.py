"""Read-only dependency readiness; camera reachability and throughput are separate."""
import asyncio
import json
import os
from pathlib import Path
import sys
import urllib.request
from urllib.parse import urlparse


def validate_redis_url(url):
    if urlparse(url).path != "/1":
        raise ValueError("production Redis database must be /1")


def check_group(client, stream, group):
    if not any(row["name"] == group for row in client.xinfo_groups(stream)):
        raise RuntimeError("consumer group missing")


def check_models(root=Path("/opt/models")):
    paths = (root / "yolov8n.pt", root / "torch/hub/checkpoints/resnet18-f37072fd.pth")
    if not all(path.is_file() and path.stat().st_size > 0 and os.access(path, os.R_OK) for path in paths):
        raise RuntimeError("preloaded model artifacts missing")


def check_process(service):
    expected = {
        "edge-cv": "argus_edge_cv", "prompt-eval": "argus_prompt_eval",
        "stream-prep": "argus_stream_prep", "stream-gateway-sync": "/app/sync.py",
    }[service]
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            args = path.read_bytes().split(b"\0")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if expected.encode() in args:
            return
    raise RuntimeError("worker process missing")


def get_json(url, token=None):
    headers = {"X-Stream-Gateway-Token": token} if token else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=3) as response:
        return json.load(response)


async def check_database():
    from argus_prompt_eval.db import get_engine
    from sqlalchemy import text
    engine = get_engine()
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


def check(service):
    check_process(service)
    if service in ("stream-gateway-sync", "stream-prep"):
        token = os.environ["STREAM_GATEWAY_TOKEN"]
        if not token:
            raise RuntimeError("internal authentication missing")
        configs = get_json(os.environ["API_INTERNAL_URL"] + "/v1/internal/stream-configs", token)
        if not isinstance(configs, list):
            raise RuntimeError("invalid camera configuration response")
        get_json(os.environ["STREAM_GATEWAY_URL"] + "/api/streams")
        if service == "stream-gateway-sync":
            path = Path(os.environ["GO2RTC_CONFIG_PATH"])
            if not path.is_file() or not os.access(path, os.W_OK):
                raise RuntimeError("gateway configuration is not writable")
            return
    import boto3
    from botocore.config import Config
    import redis
    url = os.environ["REDIS_URL"]
    validate_redis_url(url)
    with redis.Redis.from_url(url, decode_responses=True, socket_timeout=3, socket_connect_timeout=3) as client:
        client.ping()
        if service in ("edge-cv", "prompt-eval"):
            group = service
            stream = "frames:ready" if service == "edge-cv" else "candidates:ready"
            check_group(client, stream, group)
            check_group(client, "context:events", group)
    client = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT_URL"],
        aws_access_key_id=os.environ["S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["S3_SECRET_ACCESS_KEY"],
        region_name=os.environ.get("S3_REGION", "us-east-1"),
        config=Config(connect_timeout=3, read_timeout=3, retries={"max_attempts": 0}))
    try:
        client.head_bucket(Bucket=os.environ["S3_BUCKET_NAME"])
    finally:
        client.close()
    if service == "edge-cv":
        check_models()
    elif service == "prompt-eval":
        asyncio.run(asyncio.wait_for(check_database(), timeout=10))


def main(service):
    try:
        check(service)
    except Exception:
        # Exceptions may contain protected connection URLs or auth values.
        print(f"{service} dependencies not ready")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
