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

    database_url: str = Field(
        alias="DATABASE_URL",
        default="postgresql+asyncpg://argus_app:argus_app@localhost:5432/argus",
    )
    redis_url: str = Field(alias="REDIS_URL", default="redis://localhost:6379/0")

    s3_endpoint_url: str = Field(
        alias="S3_ENDPOINT_URL",
        default="http://localhost:9000",
    )
    s3_access_key_id: str = Field(alias="S3_ACCESS_KEY_ID", default="minioadmin")
    s3_secret_access_key: str = Field(
        alias="S3_SECRET_ACCESS_KEY",
        default="minioadmin",
    )
    s3_bucket_name: str = Field(alias="S3_BUCKET_NAME", default="argus-frames")
    s3_region: str = Field(alias="S3_REGION", default="us-east-1")

    auth0_domain: str = Field(alias="AUTH0_DOMAIN", default="your-tenant.auth0.com")
    auth0_api_audience: str = Field(
        alias="AUTH0_API_AUDIENCE",
        default="https://api.argus.example.com",
    )
    auth0_algorithms: str = Field(alias="AUTH0_ALGORITHMS", default="RS256")
    auth0_use_mock: bool = Field(alias="AUTH0_USE_MOCK", default=False)
    dev_jwt_secret: str = Field(
        alias="DEV_JWT_SECRET",
        default="local-dev-secret-change-me",
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
        default="https://argus.local",
    )

    admin_database_url: str = Field(
        alias="ADMIN_DATABASE_URL",
        default="postgresql+asyncpg://argus:argus@localhost:5432/argus",
    )

    openai_api_key: str = Field(alias="OPENAI_API_KEY", default="")
    openai_base_url: str = Field(alias="OPENAI_BASE_URL", default="")

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
