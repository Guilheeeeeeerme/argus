"""SQLAlchemy ORM models for ARGUS MVP multi-company surveillance data."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from argus.domain.base import Base, CompanyScopedMixin, TimestampMixin, pg_enum
from argus.domain.enums import FeedbackDisposition, TriageCaseState, UserRole

__all__ = [
    "Company",
    "CompanyUser",
    "Establishment",
    "Camera",
    "PromptSet",
    "Prompt",
    "Detection",
    "TriageCase",
    "Feedback",
    "WebhookEndpoint",
    "ContextEvent",
    "AuditRecord",
]


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(63), unique=True, nullable=False)
    aggregation_window_secs: Mapped[int] = mapped_column(
        Integer, nullable=False, default=300, server_default="300"
    )
    weird_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2, server_default="2"
    )
    warning_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default="5"
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    establishments: Mapped[list["Establishment"]] = relationship(back_populates="company")
    users: Mapped[list["CompanyUser"]] = relationship(back_populates="company")


class CompanyUser(Base, TimestampMixin):
    __tablename__ = "company_users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_company_users_email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    idp_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    role: Mapped[UserRole] = mapped_column(
        pg_enum(UserRole, "user_role"),
        nullable=False,
    )

    company: Mapped[Company | None] = relationship(back_populates="users")


class Establishment(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "establishments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(63), nullable=False, default="UTC", server_default="UTC"
    )
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    company: Mapped[Company] = relationship(back_populates="establishments")
    cameras: Mapped[list["Camera"]] = relationship(back_populates="establishment")


class Camera(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "cameras"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    establishment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("establishments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stream_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    stream_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stream_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    establishment: Mapped[Establishment] = relationship(back_populates="cameras")
    prompt_sets: Mapped[list["PromptSet"]] = relationship(back_populates="camera")


class PromptSet(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "prompt_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    camera: Mapped[Camera] = relationship(back_populates="prompt_sets")
    prompts: Mapped[list["Prompt"]] = relationship(back_populates="prompt_set")


class Prompt(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "prompts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    prompt_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    prompt_set: Mapped[PromptSet] = relationship(back_populates="prompts")


class Detection(Base, CompanyScopedMixin):
    __tablename__ = "detections"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    establishment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("establishments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_id: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    prompt_hits: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    clip_uri: Mapped[str] = mapped_column(Text, nullable=False)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_ended_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    frame_uris: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    triage_case: Mapped["TriageCase | None"] = relationship(
        back_populates="detection", uselist=False
    )


class TriageCase(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "triage_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    detection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("detections.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    state: Mapped[TriageCaseState] = mapped_column(
        pg_enum(TriageCaseState, "triage_case_state"),
        nullable=False,
        default=TriageCaseState.OPEN,
        server_default="open",
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    detection: Mapped[Detection] = relationship(back_populates="triage_case")
    feedback: Mapped[list["Feedback"]] = relationship(back_populates="triage_case")


class Feedback(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    triage_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("triage_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    disposition: Mapped[FeedbackDisposition] = mapped_column(
        pg_enum(FeedbackDisposition, "feedback_disposition"),
        nullable=False,
    )
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    triage_case: Mapped[TriageCase] = relationship(back_populates="feedback")


class WebhookEndpoint(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "webhook_endpoints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    establishment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("establishments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    context_events: Mapped[list["ContextEvent"]] = relationship(back_populates="webhook")


class ContextEvent(Base, CompanyScopedMixin):
    __tablename__ = "context_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("webhook_endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    establishment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("establishments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    camera_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(63), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    webhook: Mapped[WebhookEndpoint] = relationship(back_populates="context_events")


class AuditRecord(Base, CompanyScopedMixin, TimestampMixin):
    """Generic audit trail skeleton (no FK to dropped decision tables)."""

    __tablename__ = "audit_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    triage_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("triage_cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(63), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
