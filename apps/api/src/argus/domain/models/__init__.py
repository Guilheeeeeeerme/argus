"""SQLAlchemy ORM models for ARGUS multi-company surveillance data."""

from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Numeric,
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

from argus.domain.base import Base, CompanyScopedMixin, TimestampMixin, pg_enum
from argus.domain.enums import (
    DecisionState,
    FeedbackDisposition,
    NotificationChannel,
    NotificationStatus,
    ScheduleDay,
    UserRole,
)

__all__ = [
    "Company",
    "CompanyUser",
    "Agent",
    "AgentLocation",
    "Location",
    "Camera",
    "RegionOfInterest",
    "RuleSet",
    "RuleSetSchedule",
    "RuleSetCameraAssignment",
    "Recipe",
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

    locations: Mapped[list["Location"]] = relationship(back_populates="company")
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


class Location(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sketch: Mapped[str | None] = mapped_column(Text(), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(63), nullable=False, default="UTC", server_default="UTC"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped[Company] = relationship(back_populates="locations")
    cameras: Mapped[list["Camera"]] = relationship(back_populates="location")
    agents: Mapped[list["Agent"]] = relationship(
        secondary="agent_locations", back_populates="locations"
    )


class Agent(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("device_id", name="uq_agents_device_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    locations: Mapped[list["Location"]] = relationship(
        secondary="agent_locations", back_populates="agents"
    )


class AgentLocation(Base, CompanyScopedMixin):
    __tablename__ = "agent_locations"
    __table_args__ = (
        UniqueConstraint("agent_id", "location_id", name="uq_agent_locations_agent_location"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )


class Camera(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "cameras"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stream_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    stream_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stream_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    placement_x: Mapped[float | None] = mapped_column(nullable=True)
    placement_y: Mapped[float | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    location: Mapped[Location] = relationship(back_populates="cameras")
    regions: Mapped[list["RegionOfInterest"]] = relationship(back_populates="camera")


class RegionOfInterest(Base, CompanyScopedMixin, TimestampMixin):
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


class RuleSet(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "rule_sets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    recipes: Mapped[list["Recipe"]] = relationship(back_populates="rule_set")
    rules: Mapped[list["Rule"]] = relationship(back_populates="rule_set")


class RuleSetSchedule(Base, CompanyScopedMixin):
    __tablename__ = "rule_set_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rule_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rule_sets.id", ondelete="CASCADE"), nullable=False
    )
    day_of_week: Mapped[ScheduleDay] = mapped_column(
        pg_enum(ScheduleDay, "schedule_day"),
        nullable=False,
    )
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), nullable=True
    )


class RuleSetCameraAssignment(Base, CompanyScopedMixin):
    __tablename__ = "rule_set_camera_assignments"
    __table_args__ = (
        UniqueConstraint("camera_id", name="uq_rule_set_camera_assignments_camera"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rule_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rule_sets.id", ondelete="CASCADE"), nullable=False
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False
    )


class Recipe(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "recipes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rule_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rule_sets.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    rule_set: Mapped[RuleSet] = relationship(back_populates="recipes")


class Rule(Base, CompanyScopedMixin, TimestampMixin):
    __tablename__ = "rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rule_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rule_sets.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    detection_class: Mapped[str | None] = mapped_column(String(63), nullable=True)
    confidence_threshold: Mapped[float] = mapped_column(
        Numeric(4, 3), nullable=False, default=0.5, server_default="0.500"
    )
    condition: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    severity_weight: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )

    rule_set: Mapped[RuleSet] = relationship(back_populates="rules")
    region_mappings: Mapped[list["RuleRegionMapping"]] = relationship(back_populates="rule")


class RuleRegionMapping(Base, CompanyScopedMixin):
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


class Evidence(Base, CompanyScopedMixin):
    __tablename__ = "evidences"
    __table_args__ = (
        UniqueConstraint("company_id", "ingestion_id", name="uq_evidences_company_ingestion"),
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
    rule_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rule_sets.id", ondelete="RESTRICT"), nullable=False
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    vlm_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    detection_class: Mapped[str | None] = mapped_column(String(63), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(6, 5), nullable=True)
    severity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    frame_storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    ingestion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    decisions: Mapped[list["Decision"]] = relationship(
        secondary="decision_evidences", back_populates="evidences"
    )


class Decision(Base, CompanyScopedMixin, TimestampMixin):
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


class DecisionEvidence(Base, CompanyScopedMixin):
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


class Feedback(Base, CompanyScopedMixin, TimestampMixin):
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


class AuditRecord(Base, CompanyScopedMixin, TimestampMixin):
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


class NotificationConfig(Base, CompanyScopedMixin, TimestampMixin):
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


class NotificationDelivery(Base, CompanyScopedMixin, TimestampMixin):
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
