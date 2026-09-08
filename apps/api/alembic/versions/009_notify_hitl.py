"""Add HITL notification statuses awaiting_approval and dismissed.

Revision ID: 009_notify_hitl
Revises: 008_app_role
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op

revision: str = "009_notify_hitl"
down_revision: Union[str, None] = "008_app_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE notification_status ADD VALUE IF NOT EXISTS 'awaiting_approval'")
    op.execute("ALTER TYPE notification_status ADD VALUE IF NOT EXISTS 'dismissed'")


def downgrade() -> None:
    # PostgreSQL cannot drop enum values safely; leave values in place.
    pass
