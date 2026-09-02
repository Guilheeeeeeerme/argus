"""Core tenancy tables.

Revision ID: 002_core_tenancy
Revises: 001_enums
Create Date: 2026-09-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_core_tenancy"
down_revision: Union[str, None] = "001_enums"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = postgresql.ENUM(
    "root_admin",
    "tenant_admin",
    "watcher",
    name="user_role",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(63), nullable=False, unique=True),
        sa.Column("aggregation_window_secs", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("weird_threshold", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("warning_threshold", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default="{}"),
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

    op.create_table(
        "tenant_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("idp_subject", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("idp_subject", "tenant_id", name="uq_tenant_users_subject_tenant"),
    )
    op.create_index("ix_tenant_users_tenant_id", "tenant_users", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("tenant_users")
    op.drop_table("tenants")
