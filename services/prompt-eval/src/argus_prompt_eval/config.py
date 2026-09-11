"""Service configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        alias="DATABASE_URL",
        default="postgresql+asyncpg://argus_app:argus_app@postgres:5432/argus",
    )
    redis_url: str = Field(alias="REDIS_URL", default="redis://redis:6379/0")

    s3_endpoint_url: str = Field(alias="S3_ENDPOINT_URL", default="http://minio:9000")
    s3_public_endpoint_url: str = Field(alias="S3_PUBLIC_ENDPOINT_URL", default="")
    s3_access_key_id: str = Field(alias="S3_ACCESS_KEY_ID", default="minioadmin")
    s3_secret_access_key: str = Field(
        alias="S3_SECRET_ACCESS_KEY", default="minioadmin"
    )
    s3_bucket_name: str = Field(alias="S3_BUCKET_NAME", default="argus-frames")
    s3_region: str = Field(alias="S3_REGION", default="us-east-1")
    frame_http_allowlist: str = Field(alias="FRAME_HTTP_ALLOWLIST", default="")

    gemini_api_key: str = Field(alias="GEMINI_API_KEY", default="")
    gemini_base_url: str = Field(
        alias="GEMINI_BASE_URL",
        default="https://generativelanguage.googleapis.com",
    )
    gemini_model: str = Field(alias="GEMINI_MODEL", default="gemini-2.5-flash-lite")

    openai_api_key: str = Field(alias="OPENAI_API_KEY", default="")
    openai_base_url: str = Field(alias="OPENAI_BASE_URL", default="")
    openai_model: str = Field(alias="OPENAI_MODEL", default="gpt-4o")

    llm_provider_order: str = Field(alias="LLM_PROVIDER_ORDER", default="gemini,openai")
    llm_rate_limit_per_minute: int = Field(alias="LLM_RATE_LIMIT_PER_MINUTE", default=20)
    llm_daily_budget: int = Field(alias="LLM_DAILY_BUDGET", default=500)
    llm_global_daily_budget: int = Field(alias="LLM_GLOBAL_DAILY_BUDGET", default=5000)
    llm_daily_token_budget: int = Field(alias="LLM_DAILY_TOKEN_BUDGET", default=0)
    llm_daily_cost_usd: float = Field(alias="LLM_DAILY_COST_USD", default=0.0)
    llm_estimated_tokens_per_call: int = Field(
        alias="LLM_ESTIMATED_TOKENS_PER_CALL", default=4000
    )
    llm_estimated_cost_per_call_usd: float = Field(
        alias="LLM_ESTIMATED_COST_PER_CALL_USD", default=0.01
    )

    # Dev-only mock VLM when no provider keys are set.
    auth0_use_mock: bool = Field(alias="AUTH0_USE_MOCK", default=False)

    frames_stream: str = Field(alias="FRAMES_READY_STREAM", default="frames:ready")
    frames_group: str = Field(alias="FRAMES_READY_GROUP", default="prompt-eval")
    context_stream: str = Field(alias="CONTEXT_EVENTS_STREAM", default="context:events")
    context_group: str = Field(alias="CONTEXT_EVENTS_GROUP", default="prompt-eval")
    detections_stream: str = Field(
        alias="DETECTIONS_POSITIVE_STREAM", default="detections:positive"
    )

    confidence_floor: float = Field(alias="PROMPT_EVAL_CONFIDENCE_FLOOR", default=0.5)
    max_clip_seconds: int = Field(alias="MAX_CLIP_SECONDS", default=600)
    context_lookback_seconds: int = Field(
        alias="CONTEXT_LOOKBACK_SECONDS", default=900
    )
    rag_limit: int = Field(alias="RAG_LIMIT", default=5)
    consumer_batch_size: int = Field(alias="CONSUMER_BATCH_SIZE", default=5)
    consumer_block_ms: int = Field(alias="CONSUMER_BLOCK_MS", default=2000)

    log_level: str = Field(alias="LOG_LEVEL", default="INFO")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
