"""Google Gemini VLM integration with structured JSON output."""

from __future__ import annotations

import base64
import ipaddress
import json
import logging
from typing import Any
from urllib.parse import urlparse

import httpx

from argus.config import settings
from argus.services.storage import download_bytes

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 60
# Cap output tokens so one request cannot emit an unbounded response (LLM06).
MAX_OUTPUT_TOKENS = 2_048


def _gemini_api_root() -> str:
    return settings.gemini_base_url.rstrip("/") + "/v1beta/models"


class GeminiVLMClient:
    def analyze(
        self,
        *,
        system_prompt: str,
        frame_uris: list[str],
        output_schema: dict[str, Any],
        model: str | None = None,
        user_context: str = "",
    ) -> dict[str, Any]:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        used_model = model or settings.gemini_model
        user_parts: list[dict[str, Any]] = []
        if user_context:
            user_parts.append({"text": user_context})
        user_parts.append(
            {
                "text": (
                    "Analyze the frame sequence and respond with JSON only. "
                    f"Schema: {json.dumps(output_schema)}"
                )
            }
        )
        for uri in frame_uris:
            mime_type, data = inline_frame(uri)
            user_parts.append({"inline_data": {"mime_type": mime_type, "data": data}})

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": user_parts}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "maxOutputTokens": MAX_OUTPUT_TOKENS,
            },
        }
        response = httpx.post(
            f"{_gemini_api_root()}/{used_model}:generateContent",
            headers={"x-goog-api-key": settings.gemini_api_key},
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
        parts = _response_text_parts(body)
        return json.loads(parts)


def _response_text_parts(body: dict[str, Any]) -> str:
    candidates = body.get("candidates") or []
    if not candidates:
        raise ValueError("Gemini response contained no candidates")
    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
    joined = "".join(texts).strip()
    if not joined:
        raise ValueError("Gemini response contained no text parts")
    return joined


def inline_frame(uri: str) -> tuple[str, str]:
    """Resolve a frame URI to inline (mime_type, base64) data.

    Allowed schemes: ``data:``, ``s3://`` (via storage client credentials),
    and ``http(s):`` only when the host is on the configured frame allowlist.
    """
    if uri.startswith("data:"):
        header, _, data = uri.partition(",")
        mime_type = header.removeprefix("data:").split(";", 1)[0] or "image/jpeg"
        return mime_type, data
    if uri.startswith("s3://"):
        payload, content_type = _download_s3_sync(uri)
        mime_type = content_type if content_type.startswith("image/") else "image/jpeg"
        return mime_type, base64.b64encode(payload).decode("ascii")
    if uri.startswith(("http://", "https://")):
        mime_type, payload = _download_frame_allowlisted(uri)
        return mime_type, base64.b64encode(payload).decode("ascii")
    raise ValueError(f"Unsupported frame URI scheme for Gemini: {uri[:15]}")


def _download_s3_sync(uri: str) -> tuple[bytes, str]:
    """Sync wrapper used from the sync VLM client path."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(download_bytes(uri))).result()
    return asyncio.run(download_bytes(uri))


def _frame_http_allowlist() -> set[str]:
    raw = (settings.s3_public_endpoint_url or "").strip()
    hosts: set[str] = set()
    if raw:
        parsed = urlparse(raw if "://" in raw else f"http://{raw}")
        if parsed.hostname:
            hosts.add(parsed.hostname.lower())
    endpoint = (settings.s3_endpoint_url or "").strip()
    if endpoint:
        parsed = urlparse(endpoint if "://" in endpoint else f"http://{endpoint}")
        if parsed.hostname:
            hosts.add(parsed.hostname.lower())
    extra = (getattr(settings, "frame_http_allowlist", "") or "").strip()
    for part in extra.split(","):
        host = part.strip().lower()
        if host:
            hosts.add(host)
    return hosts


def _is_blocked_ip(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
    )


def _download_frame_allowlisted(url: str) -> tuple[str, bytes]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Frame HTTP scheme not allowed")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError("Frame URL missing host")
    if _is_blocked_ip(host):
        raise ValueError("Frame URL host is a blocked address")
    allowlist = _frame_http_allowlist()
    if not allowlist or host not in allowlist:
        raise ValueError(f"Frame URL host not allowlisted: {host}")
    response = httpx.get(
        url,
        timeout=REQUEST_TIMEOUT_SECONDS,
        follow_redirects=False,
    )
    if response.is_redirect:
        raise ValueError("Frame URL redirects are not allowed")
    response.raise_for_status()
    mime_type = response.headers.get("content-type", "").split(";", 1)[0]
    if not mime_type.startswith("image/"):
        mime_type = "image/jpeg"
    return mime_type, response.content


# Existing call sites and tests reference the private name.
_inline_frame = inline_frame
