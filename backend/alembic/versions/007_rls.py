"""Row-Level Security policies for tenant isolation.

Revision ID: 007_rls
Revises: 006_pgvector
Create Date: 2026-09-01
"""

from typing import Sequence, Union

from alembic import op

revision: str = "007_rls"
down_revision: Union[str, None] = "006_pgvector"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables with tenant_id column (tenant-scoped data)
TENANT_SCOPED_TABLES = [
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


def _enable_tenant_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_select ON {table}
            FOR SELECT
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
        """
    )
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_insert ON {table}
            FOR INSERT
            WITH CHECK (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
        """
    )
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_update ON {table}
            FOR UPDATE
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
            WITH CHECK (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
        """
    )
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_delete ON {table}
            FOR DELETE
            USING (
                tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
        """
    )
    op.execute(
        f"""
        CREATE POLICY root_admin_all ON {table}
            FOR ALL
            USING (current_setting('app.current_role', true) = 'root_admin')
            WITH CHECK (current_setting('app.current_role', true) = 'root_admin')
        """
    )


def _disable_tenant_rls(table: str) -> None:
    for policy in (
        "root_admin_all",
        "tenant_isolation_delete",
        "tenant_isolation_update",
        "tenant_isolation_insert",
        "tenant_isolation_select",
    ):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
    op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


def upgrade() -> None:
    # tenants: scope by primary key id, not tenant_id column
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenants FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation_select ON tenants
            FOR SELECT
            USING (
                id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
        """
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation_update ON tenants
            FOR UPDATE
            USING (
                id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
            WITH CHECK (
                id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
            )
        """
    )
    op.execute(
        """
        CREATE POLICY root_admin_all ON tenants
            FOR ALL
            USING (current_setting('app.current_role', true) = 'root_admin')
            WITH CHECK (current_setting('app.current_role', true) = 'root_admin')
        """
    )

    for table in TENANT_SCOPED_TABLES:
        _enable_tenant_rls(table)


def downgrade() -> None:
    for table in reversed(TENANT_SCOPED_TABLES):
        _disable_tenant_rls(table)

    for policy in ("root_admin_all", "tenant_isolation_update", "tenant_isolation_select"):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON tenants")
    op.execute("ALTER TABLE tenants NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY")
