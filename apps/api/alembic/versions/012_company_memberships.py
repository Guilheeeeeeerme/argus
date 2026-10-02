"""Add zero-to-many company memberships without replacing user identities."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "012_company_memberships"
down_revision = "011_argus_schema_grants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_user_memberships",
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("company_users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_index("ix_company_user_memberships_company_id", "company_user_memberships", ["company_id"])
    op.execute("SELECT set_config('app.current_role', 'root', true)")
    op.execute("INSERT INTO company_user_memberships (user_id, company_id) "
               "SELECT id, company_id FROM company_users WHERE company_id IS NOT NULL")
    op.execute("ALTER TABLE company_user_memberships ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE company_user_memberships FORCE ROW LEVEL SECURITY")
    # Only trusted authentication lookups and platform account administration access memberships.
    op.execute("CREATE POLICY platform_all ON company_user_memberships FOR ALL "
               "USING (current_setting('app.current_role', true) IN ('root', 'admin')) "
               "WITH CHECK (current_setting('app.current_role', true) IN ('root', 'admin'))")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON company_user_memberships TO argus_app")
    # Deleting a former primary company must not delete a multi-company identity.
    op.drop_constraint("company_users_company_id_fkey", "company_users", type_="foreignkey")
    op.create_foreign_key("company_users_company_id_fkey", "company_users", "companies",
                          ["company_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("company_users_company_id_fkey", "company_users", type_="foreignkey")
    op.create_foreign_key("company_users_company_id_fkey", "company_users", "companies",
                          ["company_id"], ["id"], ondelete="CASCADE")
    op.drop_table("company_user_memberships")
