"""Enable pgvector and add feedback embedding column.

Revision ID: 006_pgvector
Revises: 005_operational
Create Date: 2026-09-01
"""

from typing import Sequence, Union

from alembic import op

revision: str = "006_pgvector"
down_revision: Union[str, None] = "005_operational"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("ALTER TABLE feedback ADD COLUMN embedding vector(1536)")


def downgrade() -> None:
    op.drop_column("feedback", "embedding")
    op.execute("DROP EXTENSION IF EXISTS vector")
