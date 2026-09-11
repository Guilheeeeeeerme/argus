"""Environment configuration for stream-prep."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    redis_url: str = Field(alias="REDIS_URL", default="redis://redis:6379/0")

    s3_endpoint_url: str = Field(alias="S3_ENDPOINT_URL", default="http://minio:9000")
    s3_access_key_id: str = Field(alias="S3_ACCESS_KEY_ID", default="minioadmin")
    s3_secret_access_key: str = Field(alias="S3_SECRET_ACCESS_KEY", default="minioadmin")
    s3_bucket_name: str = Field(alias="S3_BUCKET_NAME", default="argus-frames")
    s3_region: str = Field(alias="S3_REGION", default="us-east-1")

    api_internal_url: str = Field(
        alias="API_INTERNAL_URL",
        default="http://api:8000",
    )
    stream_gateway_url: str = Field(
        alias="STREAM_GATEWAY_URL",
        default="http://stream-gateway:1984",
    )
    stream_gateway_token: str = Field(
        alias="STREAM_GATEWAY_TOKEN",
        default="dev-stream-gateway-token",
    )

    sample_fps: float = Field(alias="SAMPLE_FPS", default=1.0)
    """Target frames per second per camera (MVP sampling cadence)."""

    frame_ttl_seconds: int = Field(alias="FRAME_TTL", default=3600)
    """Hint for ephemeral frame lifetime (seconds); recorded in object metadata."""

    poll_interval: float = Field(alias="POLL_INTERVAL", default=30.0)
    """Seconds between stream-config refreshes from the API."""

    window_size: int = Field(alias="WINDOW_SIZE", default=6)
    """Frames per temporal window (clamped to 4–8 in temporal_window)."""

    contrast_normalize: bool = Field(alias="CONTRAST_NORMALIZE", default=False)
    """Optional contrast normalization during media preprocessing."""

    allow_synthetic_frames: bool = Field(alias="ALLOW_SYNTHETIC_FRAMES", default=True)
    """If go2rtc snapshot fails, generate a synthetic JPEG for local tests."""

    log_level: str = Field(alias="LOG_LEVEL", default="INFO")


@lru_cache
def get_settings() -> Settings:
    return Settings()
