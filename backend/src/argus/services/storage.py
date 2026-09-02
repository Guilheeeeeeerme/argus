"""S3-compatible object storage (MinIO locally) for frame sequences."""

from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import BinaryIO

import boto3
from botocore.client import BaseClient
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


async def generate_presigned_get_url(
    key: str,
    *,
    expires_in: int = 3600,
    bucket: str | None = None,
) -> str:
    bucket_name = bucket or settings.s3_bucket_name
    client = _s3_client()

    def _sign() -> str:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )

    return await asyncio.to_thread(_sign)
