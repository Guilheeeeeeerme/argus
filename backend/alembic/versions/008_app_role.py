"""Create non-superuser application role for RLS enforcement.

Revision ID: 008_app_role
Revises: 007_rls
Create Date: 2026-09-01
"""

from typing import Sequence, Union

from alembic import op

revision: str = "008_app_role"
down_revision: Union[str, None] = "007_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = [
    "tenants",
    "tenant_users",
    "markets",
    "cameras",
    "regions_of_interest",
    "context_modes",
    "context_mode_schedules",
    "context_mode_camera_assignments",
    "lenses",
    "rules",
    "rule_region_mappings",
    "evidences",
    "decisions",
    "decision_evidences",
    "feedback",
    "audit_records",
    "notification_configs",
    "notification_deliveries",
]

SEQUENCES = [f"{table}_id_seq" for table in TABLES if table not in {"decision_evidences"}]


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'argus_app') THEN
                CREATE ROLE argus_app LOGIN PASSWORD 'argus_app'
                    NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
            END IF;
        END
        $$
        """
    )
    op.execute("GRANT CONNECT ON DATABASE argus TO argus_app")
    op.execute("GRANT USAGE ON SCHEMA public TO argus_app")
    for table in TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO argus_app")
    op.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO argus_app")


def downgrade() -> None:
    op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM argus_app")
    op.execute("REVOKE USAGE ON SCHEMA public FROM argus_app")
    op.execute("DROP ROLE IF EXISTS argus_app")
