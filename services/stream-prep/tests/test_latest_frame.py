"""Latest-frame pointer: stable MinIO key + Redis hash with TTL (triage grid)."""

from datetime import datetime, timezone
from types import SimpleNamespace

from argus_stream_prep.main import StreamConfig, _publish_latest
from argus_stream_prep.redis_out import RedisOut, latest_frame_key
from argus_stream_prep.storage import FrameStorage, latest_frame_object_key

CFG = StreamConfig(camera_id="cam", account_id="tenant", unit_id="site", name="Door")


def test_latest_frame_object_key_is_stable_per_camera():
    assert latest_frame_object_key("tenant", "site", "cam") == "tenant/site/cam/latest.jpg"
    assert latest_frame_key("cam") == "frame:latest:cam"


def test_upload_latest_overwrites_with_no_store_and_captured_at():
    calls = []

    class Client:
        def put_object(self, **kwargs):
            calls.append(kwargs)

    storage = FrameStorage.__new__(FrameStorage)
    storage.settings = SimpleNamespace(s3_bucket_name="frames")
    storage._client = Client()

    uri = storage.upload_latest(
        account_id="tenant",
        unit_id="site",
        camera_id="cam",
        jpeg_bytes=b"jpeg",
        captured_at="2026-10-02T12:00:00+00:00",
    )
    assert uri == "s3://frames/tenant/site/cam/latest.jpg"
    assert calls == [
        {
            "Bucket": "frames",
            "Key": "tenant/site/cam/latest.jpg",
            "Body": b"jpeg",
            "ContentType": "image/jpeg",
            "CacheControl": "no-store",
            "Metadata": {"captured-at": "2026-10-02T12:00:00+00:00"},
        }
    ]


class FakePipeline:
    def __init__(self, log):
        self.log = log

    def hset(self, key, mapping):
        self.log.append(("hset", key, mapping))

    def expire(self, key, ttl):
        self.log.append(("expire", key, ttl))

    def execute(self):
        self.log.append(("execute",))


class FakeRedis:
    def __init__(self):
        self.log = []

    def pipeline(self, transaction=True):
        assert transaction is True
        return FakePipeline(self.log)


def test_set_latest_frame_writes_hash_and_ttl():
    out = RedisOut.__new__(RedisOut)
    out.settings = SimpleNamespace()
    out._client = FakeRedis()

    out.set_latest_frame(
        camera_id="cam",
        uri="s3://frames/tenant/site/cam/latest.jpg",
        captured_at="2026-10-02T12:00:00+00:00",
        account_id="tenant",
        unit_id="site",
        ttl_seconds=30,
    )
    assert out._client.log == [
        (
            "hset",
            "frame:latest:cam",
            {
                "uri": "s3://frames/tenant/site/cam/latest.jpg",
                "captured_at": "2026-10-02T12:00:00+00:00",
                "account_id": "tenant",
                "unit_id": "site",
            },
        ),
        ("expire", "frame:latest:cam", 30),
        ("execute",),
    ]


def test_set_latest_frame_clamps_ttl_to_at_least_one_second():
    out = RedisOut.__new__(RedisOut)
    out.settings = SimpleNamespace()
    out._client = FakeRedis()
    out.set_latest_frame(
        camera_id="cam", uri="u", captured_at="t", account_id="c", unit_id="e", ttl_seconds=0
    )
    assert ("expire", "frame:latest:cam", 1) in out._client.log


def test_publish_latest_uploads_then_points_redis_at_it():
    uploads = []
    pointers = []

    class Storage:
        def upload_latest(self, **kwargs):
            uploads.append(kwargs)
            return "s3://frames/tenant/site/cam/latest.jpg"

    class Output:
        def set_latest_frame(self, **kwargs):
            pointers.append(kwargs)

    captured_at = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
    _publish_latest(
        CFG,
        jpeg_bytes=b"jpeg",
        captured_at=captured_at,
        storage=Storage(),
        redis_out=Output(),
        settings=SimpleNamespace(latest_frame_ttl_seconds=45),
    )
    assert uploads == [
        {
            "account_id": "tenant",
            "unit_id": "site",
            "camera_id": "cam",
            "jpeg_bytes": b"jpeg",
            "captured_at": captured_at.isoformat(),
        }
    ]
    assert pointers == [
        {
            "camera_id": "cam",
            "uri": "s3://frames/tenant/site/cam/latest.jpg",
            "captured_at": captured_at.isoformat(),
            "account_id": "tenant",
            "unit_id": "site",
            "ttl_seconds": 45,
        }
    ]


def test_publish_latest_assumes_utc_for_naive_timestamps():
    pointers = []

    class Storage:
        def upload_latest(self, **kwargs):
            return "s3://x"

    class Output:
        def set_latest_frame(self, **kwargs):
            pointers.append(kwargs["captured_at"])

    _publish_latest(
        CFG,
        jpeg_bytes=b"",
        captured_at=datetime(2026, 10, 2, 12, 0),
        storage=Storage(),
        redis_out=Output(),
        settings=SimpleNamespace(latest_frame_ttl_seconds=30),
    )
    assert pointers == ["2026-10-02T12:00:00+00:00"]
