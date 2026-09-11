"""Multimodal VLM prompting — Gemini-first with OpenAI fallback.

AI Engineering pattern: Multimodal VLM prompting.
Clients return structured JSON only; frame URIs are inlined safely.
"""

from __future__ import annotations

import base64
import ipaddress
import json
import logging
from functools import lru_cache
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlparse

import httpx

from argus_prompt_eval.config import settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 60


@runtime_checkable
class VLMClient(Protocol):
    def analyze(
        self,
        *,
        system_prompt: str,
        frame_uris: list[str],
        output_schema: dict[str, Any],
        model: str | None = None,
        user_context: str = "",
    ) -> dict[str, Any]:
        """Return structured VLM analysis JSON."""


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
            mime_type, data = _inline_frame(uri)
            user_parts.append({"inline_data": {"mime_type": mime_type, "data": data}})

        root = settings.gemini_base_url.rstrip("/") + "/v1beta/models"
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": user_parts}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        response = httpx.post(
            f"{root}/{used_model}:generateContent",
            headers={"x-goog-api-key": settings.gemini_api_key},
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
        return json.loads(_response_text_parts(body))


class OpenAIVLMClient:
    def analyze(
        self,
        *,
        system_prompt: str,
        frame_uris: list[str],
        output_schema: dict[str, Any],
        model: str | None = None,
        user_context: str = "",
    ) -> dict[str, Any]:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        from openai import OpenAI

        client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
        )
        user_content: list[dict[str, Any]] = []
        if user_context:
            user_content.append({"type": "text", "text": user_context})
        user_content.append(
            {
                "type": "text",
                "text": (
                    "Analyze the frame sequence and respond with JSON only. "
                    f"Schema: {json.dumps(output_schema)}"
                ),
            }
        )
        for uri in frame_uris:
            # Prefer data URLs so OpenAI does not need MinIO network reachability.
            if uri.startswith("data:"):
                image_url = uri
            elif uri.startswith("s3://"):
                mime_type, data = _inline_frame(uri)
                image_url = f"data:{mime_type};base64,{data}"
            else:
                image_url = uri
            user_content.append(
                {"type": "image_url", "image_url": {"url": image_url}}
            )

        response = client.chat.completions.create(
            model=model or settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        return json.loads(raw)


class MockVLMClient:
    """Deterministic VLM for local/dev when provider keys are absent."""

    def __init__(self, response: dict[str, Any] | None = None) -> None:
        self.response = response or {
            "any_match": True,
            "summary": "Mock positive match for development.",
            "prompt_hits": [
                {
                    "prompt_id": "mock",
                    "matched": True,
                    "confidence": 0.91,
                    "rationale": "Deterministic mock VLM hit.",
                }
            ],
        }
        self.calls: list[dict[str, Any]] = []

    def analyze(
        self,
        *,
        system_prompt: str,
        frame_uris: list[str],
        output_schema: dict[str, Any],
        model: str | None = None,
        user_context: str = "",
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "frame_uris": frame_uris,
                "output_schema": output_schema,
                "model": model,
                "user_context": user_context,
            }
        )
        signal = f"{' '.join(frame_uris)} {system_prompt}".lower()
        if "negative" in signal or "normal" in signal:
            return {
                "any_match": False,
                "summary": "No match (mock).",
                "prompt_hits": [],
            }
        return dict(self.response)


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


def _inline_frame(uri: str) -> tuple[str, str]:
    if uri.startswith("data:"):
        header, _, data = uri.partition(",")
        mime_type = header.removeprefix("data:").split(";", 1)[0] or "image/jpeg"
        return mime_type, data
    if uri.startswith("s3://"):
        payload, content_type = download_s3_bytes(uri)
        mime_type = content_type if content_type.startswith("image/") else "image/jpeg"
        return mime_type, base64.b64encode(payload).decode("ascii")
    if uri.startswith(("http://", "https://")):
        mime_type, payload = _download_frame_allowlisted(uri)
        return mime_type, base64.b64encode(payload).decode("ascii")
    raise ValueError(f"Unsupported frame URI scheme for VLM: {uri[:15]}")


@lru_cache
def _s3_client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4"),
    )


def download_s3_bytes(uri: str) -> tuple[bytes, str]:
    bucket, key = parse_s3_uri(uri)
    client = _s3_client()
    obj = client.get_object(Bucket=bucket, Key=key)
    body = obj["Body"].read()
    content_type = obj.get("ContentType") or "application/octet-stream"
    return body, content_type


def parse_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://"):
        raise ValueError(f"Not an s3 URI: {uri[:32]}")
    without = uri.removeprefix("s3://")
    bucket, _, key = without.partition("/")
    if not bucket or not key:
        raise ValueError(f"Malformed s3 URI: {uri[:64]}")
    return bucket, key


def upload_bytes(
    key: str,
    data: bytes,
    *,
    content_type: str = "application/octet-stream",
) -> str:
    client = _s3_client()
    client.put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return f"s3://{settings.s3_bucket_name}/{key}"


def _frame_http_allowlist() -> set[str]:
    hosts: set[str] = set()
    for raw in (settings.s3_public_endpoint_url, settings.s3_endpoint_url):
        raw = (raw or "").strip()
        if not raw:
            continue
        parsed = urlparse(raw if "://" in raw else f"http://{raw}")
        if parsed.hostname:
            hosts.add(parsed.hostname.lower())
    for part in (settings.frame_http_allowlist or "").split(","):
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
    response = httpx.get(url, timeout=REQUEST_TIMEOUT_SECONDS, follow_redirects=False)
    if response.is_redirect:
        raise ValueError("Frame URL redirects are not allowed")
    response.raise_for_status()
    mime_type = response.headers.get("content-type", "").split(";", 1)[0]
    if not mime_type.startswith("image/"):
        mime_type = "image/jpeg"
    return mime_type, response.content
