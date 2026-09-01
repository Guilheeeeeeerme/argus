"""Operational surveillance tables.

Revision ID: 005_operational
Revises: 004_context_rules
Create Date: 2026-09-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_operational"
down_revision: Union[str, None] = "004_context_rules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

decision_state = postgresql.ENUM(
    "normal",
    "weird",
    "warning",
    "resolved_true_positive",
    "resolved_false_positive",
    "resolved_false_negative",
    name="decision_state",
    create_type=False,
)
feedback_disposition = postgresql.ENUM(
    "true_positive",
    "false_positive",
    "false_negative",
    name="feedback_disposition",
    create_type=False,
)
notification_channel = postgresql.ENUM(
    "sms", "whatsapp", name="notification_channel", create_type=False
)
notification_status = postgresql.ENUM(
    "pending", "sent", "delivered", "failed", name="notification_status", create_type=False
)


def upgrade() -> None:
    op.create_table(
        "evidences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cameras.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "region_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("regions_of_interest.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "context_mode_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("context_modes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("vlm_result", postgresql.JSONB(), nullable=False),
        sa.Column("severity_score", sa.Integer(), nullable=False),
        sa.Column("frame_storage_uri", sa.Text(), nullable=False),
        sa.Column("ingestion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "ingestion_id", name="uq_evidences_tenant_ingestion"),
    )
    op.create_index("ix_evidences_tenant_id", "evidences", ["tenant_id"])
    op.create_index(
        "ix_evidences_tenant_camera_captured",
        "evidences",
        ["tenant_id", "camera_id", "captured_at"],
    )

    op.create_table(
        "decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cameras.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "region_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("regions_of_interest.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("state", decision_state, nullable=False, server_default="normal"),
        sa.Column("cumulative_severity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_evidence_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_evidence_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_decisions_tenant_id", "decisions", ["tenant_id"])
    op.create_index(
        "ix_decisions_tenant_active_state",
        "decisions",
        ["tenant_id", "state"],
        postgresql_where=sa.text("state IN ('weird', 'warning')"),
    )

    op.create_table(
        "decision_evidences",
        sa.Column(
            "decision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("decisions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evidences.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "linked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_decision_evidences_tenant_id", "decision_evidences", ["tenant_id"])

    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "decision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("decisions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("disposition", feedback_disposition, nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("submitted_by", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_feedback_tenant_id", "feedback", ["tenant_id"])

    op.create_table(
        "audit_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "decision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("decisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(63), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("actor", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_audit_records_tenant_id", "audit_records", ["tenant_id"])

    op.create_table(
        "notification_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("recipient", sa.String(63), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_notification_configs_tenant_id", "notification_configs", ["tenant_id"])

    op.create_table(
        "notification_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "decision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("decisions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "config_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notification_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("status", notification_status, nullable=False, server_default="pending"),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_notification_deliveries_tenant_id", "notification_deliveries", ["tenant_id"]
    )


def downgrade() -> None:
    op.drop_table("notification_deliveries")
    op.drop_table("notification_configs")
    op.drop_table("audit_records")
    op.drop_table("feedback")
    op.drop_table("decision_evidences")
    op.drop_table("decisions")
    op.drop_table("evidences")
