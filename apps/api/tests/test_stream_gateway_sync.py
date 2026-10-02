"""The sync sidecar owns config persistence; go2rtc receives runtime PATCHes."""

import importlib.util
from pathlib import Path

import httpx


def load_sync():
    path = Path(__file__).resolve().parents[3] / "services/stream-gateway/sync.py"
    spec = importlib.util.spec_from_file_location("gateway_sync", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_live_sync_avoids_writing_readonly_gateway_config():
    sync = load_sync()
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(200 if request.method == "PATCH" else 400)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        sync.put_live_streams(
            client, {"camera-1": "ffmpeg:https://example.test/live.m3u8#video=copy"}
        )
    assert len(calls) == 1
    assert calls[0].method == "PATCH"
    assert calls[0].url.params["name"] == "camera-1"


def test_gateway_error_does_not_log_camera_credentials(caplog):
    sync = load_sync()
    source = "rtsp://operator:private-password@camera.example.test/live"
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(400, text=source))
    ) as client:
        sync.put_live_streams(client, {"camera-1": source})
    assert "status=400" in caplog.text
    assert "private-password" not in caplog.text
    assert "camera.example.test" not in caplog.text
