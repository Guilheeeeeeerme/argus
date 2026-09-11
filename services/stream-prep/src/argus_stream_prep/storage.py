"""MinIO / S3 upload for ephemeral preprocessed frames."""

from __future__ import annotations

import logging
from functools import lru_cache

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from argus_stream_prep.config import Settings, get_settings

logger = logging.getLogger(__name__)


def frame_object_key(
    company_id: str,
    establishment_id: str,
    camera_id: str,
    sequence_id: str,
    index: int,
) -> str:
    """Build ``{company}/{establishment}/{camera}/{sequence}/{n}.jpg``."""
    return f"{company_id}/{establishment_id}/{camera_id}/{sequence_id}/{index}.jpg"


class FrameStorage:
    """Upload JPEG frames to the configured S3-compatible bucket."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = _s3_client(self.settings)

    def ensure_bucket(self) -> None:
        bucket = self.settings.s3_bucket_name
        try:
            self._client.head_bucket(Bucket=bucket)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"404", "NoSuchBucket", "NotFound"}:
                self._client.create_bucket(Bucket=bucket)
                logger.info("created bucket %s", bucket)
            else:
                raise

    def upload_frame(
        self,
        *,
        company_id: str,
        establishment_id: str,
        camera_id: str,
        sequence_id: str,
        index: int,
        jpeg_bytes: bytes,
        frame_ttl_seconds: int | None = None,
    ) -> str:
        """Upload one JPEG; return ``s3://bucket/key`` URI."""
        key = frame_object_key(
            company_id, establishment_id, camera_id, sequence_id, index
        )
        ttl = frame_ttl_seconds if frame_ttl_seconds is not None else self.settings.frame_ttl_seconds
        self._client.put_object(
            Bucket=self.settings.s3_bucket_name,
            Key=key,
            Body=jpeg_bytes,
            ContentType="image/jpeg",
            Metadata={"ttl-seconds": str(ttl)},
        )
        return f"s3://{self.settings.s3_bucket_name}/{key}"


@lru_cache
def _s3_client_cached(
    endpoint: str,
    access_key: str,
    secret_key: str,
    region: str,
) -> BaseClient:
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )


def _s3_client(settings: Settings) -> BaseClient:
    return _s3_client_cached(
        settings.s3_endpoint_url,
        settings.s3_access_key_id,
        settings.s3_secret_access_key,
        settings.s3_region,
    )
