"""SSRF / allowlist tests for Gemini frame resolution."""

from __future__ import annotations

import base64

import pytest

from argus.integrations import gemini_vlm


def test_inline_data_uri_accepted() -> None:
    payload = base64.b64encode(b"fake-jpeg").decode("ascii")
    mime, data = gemini_vlm._inline_frame(f"data:image/jpeg;base64,{payload}")
    assert mime == "image/jpeg"
    assert data == payload


def test_metadata_http_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_vlm.settings, "s3_public_endpoint_url", "")
    monkeypatch.setattr(gemini_vlm.settings, "s3_endpoint_url", "http://minio:9000")
    monkeypatch.setattr(gemini_vlm.settings, "frame_http_allowlist", "")
    with pytest.raises(ValueError, match="not allowlisted|blocked"):
        gemini_vlm._inline_frame("http://169.254.169.254/latest/meta-data/")


def test_random_host_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_vlm.settings, "s3_public_endpoint_url", "http://minio:9000")
    monkeypatch.setattr(gemini_vlm.settings, "s3_endpoint_url", "http://minio:9000")
    monkeypatch.setattr(gemini_vlm.settings, "frame_http_allowlist", "")
    with pytest.raises(ValueError, match="not allowlisted"):
        gemini_vlm._inline_frame("https://evil.example/frame.jpg")


def test_allowlisted_host_no_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gemini_vlm.settings, "s3_public_endpoint_url", "http://minio:9000")
    monkeypatch.setattr(gemini_vlm.settings, "frame_http_allowlist", "minio")

    class _Resp:
        is_redirect = False
        content = b"img"
        headers = {"content-type": "image/jpeg"}

        def raise_for_status(self) -> None:
            return None

    monkeypatch.setattr(gemini_vlm.httpx, "get", lambda *a, **k: _Resp())
    mime, data = gemini_vlm._inline_frame("http://minio:9000/argus-frames/x.jpg")
    assert mime == "image/jpeg"
    assert base64.b64decode(data) == b"img"
