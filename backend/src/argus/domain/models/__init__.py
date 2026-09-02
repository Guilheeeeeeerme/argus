"""SQLAlchemy ORM models for ARGUS multi-tenant surveillance data."""

from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from argus.domain.base import Base, TenantScopedMixin, TimestampMixin, pg_enum
from argus.domain.enums import (
    DecisionState,
    FeedbackDisposition,
    NotificationChannel,
    NotificationStatus,
    ScheduleDay,
    UserRole,
)

__all__ = [
    "Tenant",
    "TenantUser",
    "Market",
    "Camera",
    "RegionOfInterest",
    "ContextMode",
    "ContextModeSchedule",
    "ContextModeCameraAssignment",
    "Lens",
    "Rule",
    "RuleRegionMapping",
    "Evidence",
    "Decision",
    "DecisionEvidence",
    "Feedback",
    "AuditRecord",
    "NotificationConfig",
    "NotificationDelivery",
]


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

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

    markets: Mapped[list["Market"]] = relationship(back_populates="tenant")
    users: Mapped[list["TenantUser"]] = relationship(back_populates="tenant")


class TenantUser(Base, TimestampMixin):
    __tablename__ = "tenant_users"
    __table_args__ = (
        UniqueConstraint("idp_subject", "tenant_id", name="uq_tenant_users_subject_tenant"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    idp_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        pg_enum(UserRole, "user_role"),
        nullable=False,
    )

    tenant: Mapped[Tenant | None] = relationship(back_populates="users")


class Market(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "markets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(63), nullable=False, default="UTC", server_default="UTC"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped[Tenant] = relationship(back_populates="markets")
    cameras: Mapped[list["Camera"]] = relationship(back_populates="market")


class Camera(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "cameras"
    __table_args__ = (
        UniqueConstraint("tenant_id", "edge_device_id", name="uq_cameras_tenant_edge_device"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    market_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("markets.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    edge_device_id: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    market: Mapped[Market] = relationship(back_populates="cameras")
    regions: Mapped[list["RegionOfInterest"]] = relationship(back_populates="camera")


class RegionOfInterest(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "regions_of_interest"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    polygon: Mapped[list[dict[str, float]]] = mapped_column(JSONB, nullable=False)

    camera: Mapped[Camera] = relationship(back_populates="regions")


class ContextMode(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "context_modes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    lenses: Mapped[list["Lens"]] = relationship(back_populates="context_mode")
    rules: Mapped[list["Rule"]] = relationship(back_populates="context_mode")


class ContextModeSchedule(Base, TenantScopedMixin):
    __tablename__ = "context_mode_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    context_mode_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("context_modes.id", ondelete="CASCADE"), nullable=False
    )
    day_of_week: Mapped[ScheduleDay] = mapped_column(
        pg_enum(ScheduleDay, "schedule_day"),
        nullable=False,
    )
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    market_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("markets.id", ondelete="CASCADE"), nullable=True
    )


class ContextModeCameraAssignment(Base, TenantScopedMixin):
    __tablename__ = "context_mode_camera_assignments"
    __table_args__ = (
        UniqueConstraint("camera_id", name="uq_context_mode_camera_assignments_camera"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    context_mode_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("context_modes.id", ondelete="CASCADE"), nullable=False
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
    )


class Lens(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "lenses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    context_mode_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("context_modes.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    context_mode: Mapped[ContextMode] = relationship(back_populates="lenses")


class Rule(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    context_mode_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("context_modes.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    condition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    severity_weight: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )

    context_mode: Mapped[ContextMode] = relationship(back_populates="rules")
    region_mappings: Mapped[list["RuleRegionMapping"]] = relationship(back_populates="rule")


class RuleRegionMapping(Base, TenantScopedMixin):
    __tablename__ = "rule_region_mappings"
    __table_args__ = (
        UniqueConstraint("rule_id", "region_id", name="uq_rule_region_mappings_rule_region"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rules.id", ondelete="CASCADE"), nullable=False
    )
    region_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regions_of_interest.id", ondelete="CASCADE"),
        nullable=False,
    )

    rule: Mapped[Rule] = relationship(back_populates="region_mappings")


class Evidence(Base, TenantScopedMixin):
    __tablename__ = "evidences"
    __table_args__ = (
        UniqueConstraint("tenant_id", "ingestion_id", name="uq_evidences_tenant_ingestion"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
    )
    region_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regions_of_interest.id", ondelete="SET NULL"),
        nullable=True,
    )
    context_mode_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("context_modes.id", ondelete="RESTRICT"), nullable=False
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    vlm_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    severity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    frame_storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    ingestion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    decisions: Mapped[list["Decision"]] = relationship(
        secondary="decision_evidences", back_populates="evidences"
    )


class Decision(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
    )
    region_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regions_of_interest.id", ondelete="SET NULL"),
        nullable=True,
    )
    state: Mapped[DecisionState] = mapped_column(
        pg_enum(DecisionState, "decision_state"),
        nullable=False,
        default=DecisionState.NORMAL,
        server_default="normal",
    )
    cumulative_severity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    evidence_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_evidence_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_evidence_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    evidences: Mapped[list[Evidence]] = relationship(
        secondary="decision_evidences", back_populates="decisions"
    )
    feedback: Mapped["Feedback | None"] = relationship(back_populates="decision", uselist=False)


class DecisionEvidence(Base, TenantScopedMixin):
    __tablename__ = "decision_evidences"

    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evidences.id", ondelete="CASCADE"),
        primary_key=True,
    )
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Feedback(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("decisions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    disposition: Mapped[FeedbackDisposition] = mapped_column(
        pg_enum(FeedbackDisposition, "feedback_disposition"),
        nullable=False,
    )
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_by: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    decision: Mapped[Decision] = relationship(back_populates="feedback")


class AuditRecord(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "audit_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(63), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)


class NotificationConfig(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "notification_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        pg_enum(NotificationChannel, "notification_channel"),
        nullable=False,
    )
    recipient: Mapped[str] = mapped_column(String(63), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class NotificationDelivery(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "notification_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False
    )
    config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notification_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        pg_enum(NotificationChannel, "notification_channel"),
        nullable=False,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        pg_enum(NotificationStatus, "notification_status"),
        nullable=False,
        default=NotificationStatus.PENDING,
        server_default="pending",
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
