"""SQLAlchemy declarative base and shared mixins."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def pg_enum(enum_type: type[enum.Enum], name: str) -> SAEnum:
    """Map Python str enums to PostgreSQL ENUM values (not member names)."""
    return SAEnum(
        enum_type,
        name=name,
        values_callable=lambda choices: [choice.value for choice in choices],
        native_enum=True,
        create_constraint=False,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class TenantScopedMixin:
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
