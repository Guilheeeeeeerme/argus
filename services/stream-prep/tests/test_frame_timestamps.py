from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from argus_stream_prep.main import _publish_window


def test_window_preserves_individual_capture_times():
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    samples = [
        SimpleNamespace(
            captured_at=start + timedelta(seconds=i),
            payload=SimpleNamespace(
                jpeg_bytes=b"jpeg", meta=SimpleNamespace(to_dict=lambda: {"width": 20})
            ),
        )
        for i in (0, 4)
    ]
    window = SimpleNamespace(
        company_id="tenant",
        establishment_id="site",
        camera_id="camera",
        sequence_id="sequence",
        captured_at=samples[-1].captured_at,
        frames=samples,
    )

    class Storage:
        def upload_frame(self, **kwargs):
            return "s3://frames/" + str(kwargs["index"])

    class Output:
        def publish_frames_ready(self, **kwargs):
            self.published = kwargs

    output = Output()
    _publish_window(
        window,
        storage=Storage(),
        redis_out=output,
        settings=SimpleNamespace(frame_ttl_seconds=3600),
    )
    assert output.published["frame_uris"] == ["s3://frames/0", "s3://frames/1"]
    assert [m["captured_at"] for m in output.published["preproc_meta"]["frames"]] == [
        sample.captured_at.isoformat() for sample in samples
    ]
    assert output.published["captured_at"] == samples[-1].captured_at.isoformat()
