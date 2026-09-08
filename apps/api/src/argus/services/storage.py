"""S3-compatible object storage (MinIO locally) for frame sequences."""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import BinaryIO

import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import ClientError

from argus.config import settings


@lru_cache
def _s3_client() -> BaseClient:
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
    )


async def ensure_bucket_exists(bucket: str | None = None) -> bool:
    bucket_name = bucket or settings.s3_bucket_name
    client = _s3_client()

    def _check() -> bool:
        try:
            client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"404", "NoSuchBucket", "NotFound"}:
                client.create_bucket(Bucket=bucket_name)
                return True
            raise

    return await asyncio.to_thread(_check)


async def upload_bytes(
    key: str,
    data: bytes,
    *,
    content_type: str = "application/octet-stream",
    bucket: str | None = None,
) -> str:
    bucket_name = bucket or settings.s3_bucket_name
    client = _s3_client()

    def _upload() -> str:
        client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return f"s3://{bucket_name}/{key}"

    return await asyncio.to_thread(_upload)


async def upload_fileobj(
    key: str,
    fileobj: BinaryIO,
    *,
    content_type: str = "application/octet-stream",
    bucket: str | None = None,
) -> str:
    bucket_name = bucket or settings.s3_bucket_name
    client = _s3_client()

    def _upload() -> str:
        client.upload_fileobj(
            fileobj,
            bucket_name,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return f"s3://{bucket_name}/{key}"

    return await asyncio.to_thread(_upload)


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """Parse ``s3://bucket/key`` into (bucket, key)."""
    if not uri.startswith("s3://"):
        raise ValueError(f"Not an s3 URI: {uri[:32]}")
    without = uri.removeprefix("s3://")
    bucket, _, key = without.partition("/")
    if not bucket or not key:
        raise ValueError(f"Malformed s3 URI: {uri[:64]}")
    return bucket, key


async def download_bytes(uri: str) -> tuple[bytes, str]:
    """Fetch object bytes for an ``s3://`` URI. Returns (payload, content_type)."""
    bucket_name, key = parse_s3_uri(uri)
    client = _s3_client()

    def _get() -> tuple[bytes, str]:
        response = client.get_object(Bucket=bucket_name, Key=key)
        body = response["Body"].read()
        content_type = (response.get("ContentType") or "application/octet-stream").split(
            ";", 1
        )[0]
        return body, content_type

    return await asyncio.to_thread(_get)


async def generate_presigned_get_url(
    key: str,
    *,
    expires_in: int = 3600,
    bucket: str | None = None,
) -> str:
    bucket_name = bucket or settings.s3_bucket_name
    client = _public_s3_client()

    def _sign() -> str:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )

    return await asyncio.to_thread(_sign)


@lru_cache
def _public_s3_client() -> BaseClient:
    if not settings.s3_public_endpoint_url:
        return _s3_client()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_public_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
