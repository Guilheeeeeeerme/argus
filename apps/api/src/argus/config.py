"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

ServiceRole = Literal[
    "api-admin",
    "api-ingest",
    "ws-gateway",
    "worker-vlm",
    "worker-aggregator",
    "worker-notify",
    "worker-scheduler",
]

DEFAULT_PORTS: dict[str, int] = {
    "api-admin": 8000,
    "api-ingest": 8001,
    "ws-gateway": 8002,
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_role: ServiceRole = Field(alias="SERVICE_ROLE", default="api-admin")

    cors_origins: str = Field(
        alias="CORS_ORIGINS",
        default=(
            "http://localhost:8180,http://localhost:8181,"
            "http://127.0.0.1:8180,http://127.0.0.1:8181"
        ),
    )
    triage_public_origin: str = Field(
        alias="TRIAGE_PUBLIC_ORIGIN",
        default="http://localhost:8181",
    )
    stream_gateway_token: str = Field(
        alias="STREAM_GATEWAY_TOKEN",
        default="dev-stream-gateway-token",
    )

    database_url: str = Field(
        alias="DATABASE_URL",
        default="postgresql+asyncpg://argus_app:argus_app@postgres:5432/argus",
    )
    redis_url: str = Field(alias="REDIS_URL", default="redis://redis:6379/0")

    s3_endpoint_url: str = Field(
        alias="S3_ENDPOINT_URL",
        default="http://minio:9000",
    )
    s3_public_endpoint_url: str = Field(alias="S3_PUBLIC_ENDPOINT_URL", default="")
    s3_access_key_id: str = Field(alias="S3_ACCESS_KEY_ID", default="minioadmin")
    s3_secret_access_key: str = Field(
        alias="S3_SECRET_ACCESS_KEY",
        default="minioadmin",
    )
    s3_bucket_name: str = Field(alias="S3_BUCKET_NAME", default="argus-frames")
    s3_region: str = Field(alias="S3_REGION", default="us-east-1")

    auth0_domain: str = Field(alias="AUTH0_DOMAIN", default="dev.local")
    auth0_api_audience: str = Field(
        alias="AUTH0_API_AUDIENCE",
        default="http://localhost:8800",
    )
    auth0_algorithms: str = Field(alias="AUTH0_ALGORITHMS", default="RS256")
    auth0_use_mock: bool = Field(alias="AUTH0_USE_MOCK", default=False)
    dev_jwt_secret: str = Field(
        alias="DEV_JWT_SECRET",
        default="local-dev-secret-change-me",
    )
    dev_root_email: str = Field(alias="DEV_ROOT_EMAIL", default="root@argus.local")
    dev_root_password: str = Field(
        alias="DEV_ROOT_PASSWORD", default="local-root-password"
    )
    dev_notify_fail: bool = Field(alias="DEV_NOTIFY_FAIL", default=False)
    notification_mode: Literal["log", "twilio"] = Field(alias="NOTIFICATION_MODE", default="log")
    event_transport: Literal["log", "sns", "eventbridge"] = Field(alias="EVENT_TRANSPORT", default="log")
    aws_region: str = Field(alias="AWS_REGION", default="us-east-1")
    aws_access_key_id: str = Field(alias="AWS_ACCESS_KEY_ID", default="")
    aws_secret_access_key: str = Field(alias="AWS_SECRET_ACCESS_KEY", default="")
    sns_topic_arn: str = Field(alias="SNS_TOPIC_ARN", default="")
    eventbridge_bus_name: str = Field(alias="EVENTBRIDGE_BUS_NAME", default="default")
    auth0_claims_namespace: str = Field(
        alias="AUTH0_CLAIMS_NAMESPACE",
        default="http://argus.local",
    )

    admin_database_url: str = Field(
        alias="ADMIN_DATABASE_URL",
        default="postgresql+asyncpg://argus:argus@postgres:5432/argus",
    )

    openai_api_key: str = Field(alias="OPENAI_API_KEY", default="")
    openai_base_url: str = Field(alias="OPENAI_BASE_URL", default="")
    openai_model: str = Field(alias="OPENAI_MODEL", default="gpt-4o")

    gemini_api_key: str = Field(alias="GEMINI_API_KEY", default="")
    gemini_model: str = Field(alias="GEMINI_MODEL", default="gemini-2.5-flash-lite")
    llm_provider_order: str = Field(alias="LLM_PROVIDER_ORDER", default="gemini,openai")
    model_rank_refresh_ms: int = Field(alias="MODEL_RANK_REFRESH_MS", default=43200000)
    model_rank_top_n: int = Field(alias="MODEL_RANK_TOP_N", default=3)
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
    vlm_min_confidence_for_hint: float = Field(
        alias="VLM_MIN_CONFIDENCE_FOR_HINT", default=0.55
    )
    frame_http_allowlist: str = Field(alias="FRAME_HTTP_ALLOWLIST", default="")
    rate_limit_per_minute: int = Field(alias="RATE_LIMIT_PER_MINUTE", default=30)

    twilio_account_sid: str = Field(alias="TWILIO_ACCOUNT_SID", default="")
    twilio_auth_token: str = Field(alias="TWILIO_AUTH_TOKEN", default="")
    twilio_sms_from: str = Field(alias="TWILIO_SMS_FROM", default="")
    twilio_whatsapp_from: str = Field(alias="TWILIO_WHATSAPP_FROM", default="")

    api_host: str = Field(alias="API_HOST", default="0.0.0.0")
    api_port: int = Field(alias="API_PORT", default=8000)

    log_level: str = Field(alias="LOG_LEVEL", default="INFO")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def auth0_jwks_url(self) -> str:
        return f"https://{self.auth0_domain}/.well-known/jwks.json"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def auth0_issuer(self) -> str:
        return f"https://{self.auth0_domain}/"

    def resolved_api_port(self) -> int:
        return DEFAULT_PORTS.get(self.service_role, self.api_port)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
