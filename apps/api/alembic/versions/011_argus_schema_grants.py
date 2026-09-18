"""Ensure argus_app has DML grants on schema argus (Supabase).

Revision ID: 011_argus_schema_grants
Revises: 010_mvp_domain
Create Date: 2026-09-18
"""

from typing import Sequence, Union

from alembic import op

revision: str = "011_argus_schema_grants"
down_revision: Union[str, None] = "010_mvp_domain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'argus')
             AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'argus_app') THEN
            GRANT USAGE ON SCHEMA argus TO argus_app;
            GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA argus TO argus_app;
            GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA argus TO argus_app;
            ALTER DEFAULT PRIVILEGES IN SCHEMA argus
              GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO argus_app;
          END IF;
        END
        $$
        """
    )


def downgrade() -> None:
    pass
