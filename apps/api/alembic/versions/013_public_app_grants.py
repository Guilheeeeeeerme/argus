"""Grant argus_app DML on the MVP domain tables created in public after 008.

Migration 008 granted the app role on the tables that existed at the time and
set default privileges only for the Supabase `argus` schema. Tables added by
010/012 in a plain `public` layout (local compose, fresh volumes) were never
granted, so `argus_app` could not read `establishments`, `detections`, etc.

Grants are per-table and guarded by `to_regclass`, so on Supabase (schema
`argus`) nothing in an unrelated `public` schema is touched.
"""

from alembic import op

revision = "013_public_app_grants"
down_revision = "012_company_memberships"
branch_labels = None
depends_on = None

TABLES = (
    "companies",
    "company_users",
    "company_user_memberships",
    "establishments",
    "cameras",
    "prompt_sets",
    "prompts",
    "detections",
    "triage_cases",
    "feedback",
    "webhook_endpoints",
    "context_events",
    "audit_records",
)


def upgrade() -> None:
    for table in TABLES:
        op.execute(
            f"""
            DO $$
            BEGIN
              IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'argus_app')
                 AND to_regclass('public.{table}') IS NOT NULL THEN
                EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON public.{table} TO argus_app';
              END IF;
            END
            $$
            """
        )
    # Future tables in a public-only layout inherit the grant; Supabase keeps
    # the `argus` schema default privileges from 008/011 untouched.
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'argus_app')
             AND NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'argus') THEN
            GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO argus_app;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public
              GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO argus_app;
          END IF;
        END
        $$
        """
    )


def downgrade() -> None:
    # Grants are additive and safe to keep; 008's downgrade revokes everything.
    pass
