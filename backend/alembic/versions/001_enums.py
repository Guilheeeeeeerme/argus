"""Create PostgreSQL ENUM types.

Revision ID: 001_enums
Revises:
Create Date: 2026-09-01
"""

from typing import Sequence, Union

from alembic import op

revision: str = "001_enums"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE user_role AS ENUM ('root_admin', 'tenant_admin', 'watcher')")
    op.execute(
        "CREATE TYPE decision_state AS ENUM ("
        "'normal', 'weird', 'warning', "
        "'resolved_true_positive', 'resolved_false_positive', 'resolved_false_negative'"
        ")"
    )
    op.execute(
        "CREATE TYPE feedback_disposition AS ENUM ("
        "'true_positive', 'false_positive', 'false_negative'"
        ")"
    )
    op.execute("CREATE TYPE notification_channel AS ENUM ('sms', 'whatsapp')")
    op.execute(
        "CREATE TYPE notification_status AS ENUM ('pending', 'sent', 'delivered', 'failed')"
    )
    op.execute(
        "CREATE TYPE schedule_day AS ENUM ("
        "'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'"
        ")"
    )


def downgrade() -> None:
    op.execute("DROP TYPE IF EXISTS schedule_day")
    op.execute("DROP TYPE IF EXISTS notification_status")
    op.execute("DROP TYPE IF EXISTS notification_channel")
    op.execute("DROP TYPE IF EXISTS feedback_disposition")
    op.execute("DROP TYPE IF EXISTS decision_state")
    op.execute("DROP TYPE IF EXISTS user_role")
