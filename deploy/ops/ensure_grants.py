"""Re-apply runtime-role grants for `argus_app` (idempotent, run as `argus`).

Extracted from alembic revisions 008_app_role and 011_argus_schema_grants using
the same guarded DO-blocks, so re-running after a deployment (or after new
tables appear) keeps the runtime role's props correct:

- `argus_app` (if missing) is created as a LOGIN with NOSUPERUSER, NOBYPASSRLS,
  NOCREATEDB, NOCREATEROLE; when `ARGUS_APP_ROLE_PASSWORD` is provided it is
  used to set the initial password so the runtime DATABASE_URL can connect.
- Schema/table/sequence DML grants in `argus` (Supabase) and `public`
  (local) schemas, plus default privileges for future tables.

Driven by ADMIN_DATABASE_URL (owner role `argus`, which IS the DB owner on the
existing Supabase project). Never grants owner abilities to argus_app; the two
roles stay distinct (hard rule).

Usage:
    python deploy/ops/ensure_grants.py            # apply
    python deploy/ops/ensure_grants.py --print    # print SQL only
"""

from __future__ import annotations

import argparse
import asyncio
import os

import asyncpg

# revisions 008 (tables) + 011 (schema-wide consolidation).
TABLES = [
    "account_users",
    "companies",
    "company_users",
    "agents",
    "agent_locations",
    "locations",
    "units",
    "cameras",
    "regions_of_interest",
    "rule_sets",
    "rule_set_schedules",
    "rule_set_camera_assignments",
    "recipes",
    "rules",
    "rule_region_mappings",
    "evidences",
    "decisions",
    "decision_evidences",
    "feedback",
    "audit_records",
    "notification_configs",
    "notification_deliveries",
    "account_memberships",
]


def _create_role_password_clause() -> str:
    """SQL password literal from ARGUS_APP_ROLE_PASSWORD (empty = no clause)."""
    password = os.environ.get("ARGUS_APP_ROLE_PASSWORD", "")
    if not password:
        return ""
    return " PASSWORD '" + password + "'"


STATEMENTS = [
    # Role props (008): idempotent create. Password only when the role must be
    # created; ARGUS_APP_ROLE_PASSWORD should match the password in the runtime
    # DATABASE_URL. Never reset the password here.
    """
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'argus_app') THEN
            CREATE ROLE argus_app LOGIN
                NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE%(pwd)s;
        END IF;
    END
    $$
    """ % {"pwd": _create_role_password_clause()},
    """
    DO $$
    BEGIN
      EXECUTE format('GRANT CONNECT ON DATABASE %I TO argus_app', current_database());
    END
    $$
    """,
    "GRANT USAGE ON SCHEMA public TO argus_app",
    # Schema `argus` grants (008 + 011).
    """
    DO $$
    BEGIN
      IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'argus') THEN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'argus_app') THEN
          RAISE EXCEPTION 'argus_app role missing';
        END IF;
        GRANT USAGE ON SCHEMA argus TO argus_app;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA argus TO argus_app;
        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA argus TO argus_app;
        ALTER DEFAULT PRIVILEGES IN SCHEMA argus
          GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO argus_app;
      END IF;
    END
    $$
    """,
    # public-schema table grants (008): local/VPS layout compat.
    *[f"""
    DO $$
    BEGIN
      IF to_regclass('public.{table}') IS NOT NULL THEN
        EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON public.{table} TO argus_app';
      END IF;
    END
    $$
    """ for table in TABLES],
    "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO argus_app",
    """
    DO $$
    BEGIN
      IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'argus') THEN
        GRANT USAGE ON ALL SEQUENCES IN SCHEMA argus TO argus_app;
      END IF;
    END
    $$
    """,
    # Re-assert NOBYPASSRLS posture on whatever role state exists (008 props).
    """
    DO $$
    BEGIN
      IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'argus_app'
                 AND (rolbypassrls OR rolsuper OR rolcreatedb OR rolcreaterole)) THEN
        ALTER ROLE argus_app NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
      END IF;
    END
    $$
    """,
]


def admin_dsn() -> str:
    url = os.environ.get("ADMIN_DATABASE_URL", "")
    if not url:
        raise SystemExit("ADMIN_DATABASE_URL is required")
    return url


async def apply(sql_statements: list[str], dry_run: bool) -> None:
    for statement in sql_statements:
        if dry_run:
            print(statement.strip(), end="\n\n")
            continue
        conn = await asyncpg.connect()
        try:
            await conn.execute(statement)
        finally:
            await conn.close()
    if not dry_run:
        print("ensure_grants: role grants for argus_app applied")


def main() -> None:
    parser = argparse.ArgumentParser(description="apply/reprint argus_app grants")
    parser.add_argument("--print", dest="print_only", action="store_true")
    args = parser.parse_args()
    statements = [s.strip() for s in STATEMENTS]
    asyncio.run(apply(statements, args.print_only))


if __name__ == "__main__":
    main()
