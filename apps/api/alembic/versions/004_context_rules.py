"""Context modes, recipes, and rules.

Revision ID: 004_context_rules
Revises: 003_surveillance_config
Create Date: 2026-09-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_context_rules"
down_revision: Union[str, None] = "003_surveillance_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

schedule_day = postgresql.ENUM(
    "mon", "tue", "wed", "thu", "fri", "sat", "sun",
    name="schedule_day",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "rule_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_rule_sets_company_id", "rule_sets", ["company_id"])

    op.create_table(
        "rule_set_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rule_set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rule_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("day_of_week", schedule_day, nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column(
            "location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("locations.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_rule_set_schedules_company_id", "rule_set_schedules", ["company_id"]
    )

    op.create_table(
        "rule_set_camera_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rule_set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rule_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cameras.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("camera_id", name="uq_rule_set_camera_assignments_camera"),
    )
    op.create_index(
        "ix_rule_set_camera_assignments_company_id",
        "rule_set_camera_assignments",
        ["company_id"],
    )

    op.create_table(
        "recipes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rule_set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rule_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("output_schema", postgresql.JSONB(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_recipes_company_id", "recipes", ["company_id"])

    op.create_table(
        "rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rule_set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rule_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("detection_class", sa.String(63), nullable=True),
        sa.Column("confidence_threshold", sa.Numeric(4, 3), nullable=False, server_default="0.500"),
        sa.Column("condition", postgresql.JSONB(), nullable=False),
        sa.Column("severity_weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_rules_company_id", "rules", ["company_id"])

    op.create_table(
        "rule_region_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "region_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("regions_of_interest.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("rule_id", "region_id", name="uq_rule_region_mappings_rule_region"),
    )
    op.create_index("ix_rule_region_mappings_company_id", "rule_region_mappings", ["company_id"])


def downgrade() -> None:
    op.drop_table("rule_region_mappings")
    op.drop_table("rules")
    op.drop_table("recipes")
    op.drop_table("rule_set_camera_assignments")
    op.drop_table("rule_set_schedules")
    op.drop_table("rule_sets")
