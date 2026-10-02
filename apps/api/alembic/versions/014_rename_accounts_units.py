"""Rename Company → Account and Establishment → Unit (tables, columns, RLS, GUC).

Product vocabulary: *Conta / Account* (company, NGO, school, university) and
*Unidade / Unit* (store, room, campus). Everything that carried the old names is
renamed in one reversible step:

- tables: companies→accounts, company_users→account_users,
  company_user_memberships→account_user_memberships, establishments→units
- columns: company_id→account_id, establishment_id→unit_id
- constraints and indexes: renamed from a catalog scan through `_rename_map`,
  because generated names can differ between Supabase and local volumes
- RLS: policies dropped and recreated against `app.current_account_id`
- `accounts.kind account_kind NOT NULL DEFAULT 'company'`

The scan is schema-aware (`current_schema()` follows the search_path that
alembic/env.py sets to `argus` on Supabase), so unrelated `public` objects are
never touched there. Not compatible with the previous application code: deploy
the matching release in the same maintenance window.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "014_rename_accounts_units"
down_revision = "013_public_app_grants"
branch_labels = None
depends_on = None

# (old, new) in dependency-safe order.
TABLE_RENAMES = (
    ("companies", "accounts"),
    ("company_users", "account_users"),
    ("company_user_memberships", "account_user_memberships"),
    ("establishments", "units"),
)
# Tables carrying the tenant column (new names).
ACCOUNT_COLUMN_TABLES = (
    "account_users",
    "account_user_memberships",
    "units",
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
UNIT_COLUMN_TABLES = ("cameras", "detections", "webhook_endpoints", "context_events")
# Full tenant policy set (select/insert/update/delete on the tenant column + platform_all).
TENANT_RLS_TABLES = (
    "account_users",
    "units",
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
ALL_NEW_TABLES = ("accounts", "account_user_memberships", *TENANT_RLS_TABLES)

# Longest tokens first so `company_users` is not split into `company` + `_users`.
_UP_TOKENS = (
    ("company_user_memberships", "account_user_memberships"),
    ("company_users", "account_users"),
    ("companies", "accounts"),
    ("company_id", "account_id"),
    ("company", "account"),
    ("establishments", "units"),
    ("establishment_id", "unit_id"),
    ("establishment", "unit"),
)
_DOWN_TOKENS = tuple((new, old) for old, new in _UP_TOKENS)


def _rename_map(name: str, direction: str) -> str:
    """Translate an identifier between the two vocabularies ("up" or "down")."""
    tokens = _UP_TOKENS if direction == "up" else _DOWN_TOKENS
    for old, new in tokens:
        name = name.replace(old, new)
    return name


def _old(table: str) -> str:
    return _rename_map(table, "down")


# ——— catalog helpers (schema-aware through current_schema()) ———


def _drop_policies(tables: tuple[str, ...]) -> None:
    conn = op.get_bind()
    rows = conn.execute(
        text(
            "SELECT tablename, policyname FROM pg_policies "
            "WHERE schemaname = current_schema() AND tablename = ANY(:tables)"
        ),
        {"tables": list(tables)},
    ).all()
    for table, policy in rows:
        op.execute(f'DROP POLICY IF EXISTS "{policy}" ON "{table}"')


def _rename_constraints_and_indexes(tables: tuple[str, ...], direction: str) -> None:
    conn = op.get_bind()
    constraints = conn.execute(
        text(
            "SELECT c.relname, con.conname FROM pg_constraint con "
            "JOIN pg_class c ON c.oid = con.conrelid "
            "WHERE c.relnamespace = current_schema()::regnamespace AND c.relname = ANY(:tables)"
        ),
        {"tables": list(tables)},
    ).all()
    for table, name in constraints:
        target = _rename_map(name, direction)
        if target != name:
            op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{name}" TO "{target}"')
    # Indexes that are not owned by a constraint (constraint renames already renamed theirs).
    indexes = conn.execute(
        text(
            "SELECT i.tablename, i.indexname FROM pg_indexes i "
            "WHERE i.schemaname = current_schema() AND i.tablename = ANY(:tables) "
            "AND NOT EXISTS (SELECT 1 FROM pg_constraint con "
            "  WHERE con.conindid = (quote_ident(i.schemaname) || '.' || quote_ident(i.indexname))::regclass)"
        ),
        {"tables": list(tables)},
    ).all()
    for _table, name in indexes:
        target = _rename_map(name, direction)
        if target != name:
            op.execute(f'ALTER INDEX "{name}" RENAME TO "{target}"')


def _policy_sql(table: str, column: str, guc: str) -> list[str]:
    predicate = f"{column} = NULLIF(current_setting('{guc}', true), '')::uuid"
    return [
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY",
        f"CREATE POLICY tenant_isolation_select ON {table} FOR SELECT USING ({predicate})",
        f"CREATE POLICY tenant_isolation_insert ON {table} FOR INSERT WITH CHECK ({predicate})",
        f"CREATE POLICY tenant_isolation_update ON {table} FOR UPDATE USING ({predicate}) WITH CHECK ({predicate})",
        f"CREATE POLICY tenant_isolation_delete ON {table} FOR DELETE USING ({predicate})",
        _platform_policy(table),
    ]


def _platform_policy(table: str) -> str:
    return (
        f"CREATE POLICY platform_all ON {table} FOR ALL "
        "USING (current_setting('app.current_role', true) IN ('root', 'admin')) "
        "WITH CHECK (current_setting('app.current_role', true) IN ('root', 'admin'))"
    )


def _create_rls(direction: str) -> None:
    """Recreate every policy for the vocabulary of `direction` ("up" = account)."""
    if direction == "up":
        root, memberships, column, guc = "accounts", "account_user_memberships", "account_id", "app.current_account_id"
    else:
        root, memberships, column, guc = "companies", "company_user_memberships", "company_id", "app.current_company_id"
    for table in TENANT_RLS_TABLES:
        name = table if direction == "up" else _old(table)
        for statement in _policy_sql(name, column, guc):
            op.execute(statement)
    predicate = f"id = NULLIF(current_setting('{guc}', true), '')::uuid"
    for statement in (
        f"ALTER TABLE {root} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {root} FORCE ROW LEVEL SECURITY",
        f"CREATE POLICY tenant_isolation_select ON {root} FOR SELECT USING ({predicate})",
        f"CREATE POLICY tenant_isolation_update ON {root} FOR UPDATE USING ({predicate}) WITH CHECK ({predicate})",
        _platform_policy(root),
        f"ALTER TABLE {memberships} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {memberships} FORCE ROW LEVEL SECURITY",
        _platform_policy(memberships),
    ):
        op.execute(statement)


def _regrant(tables: tuple[str, ...]) -> None:
    for table in tables:
        op.execute(
            f"""
            DO $$
            BEGIN
              IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'argus_app')
                 AND to_regclass('{table}') IS NOT NULL THEN
                EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO argus_app';
              END IF;
            END
            $$
            """
        )


# ——— migration ———


def upgrade() -> None:
    old_tables = tuple(_old(t) for t in ALL_NEW_TABLES)
    _drop_policies(old_tables)
    for old, new in TABLE_RENAMES:
        op.rename_table(old, new)
    for table in ACCOUNT_COLUMN_TABLES:
        op.alter_column(table, "company_id", new_column_name="account_id")
    for table in UNIT_COLUMN_TABLES:
        op.alter_column(table, "establishment_id", new_column_name="unit_id")
    _rename_constraints_and_indexes(ALL_NEW_TABLES, "up")
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                         WHERE t.typname = 'account_kind' AND n.nspname = current_schema()) THEN
            CREATE TYPE account_kind AS ENUM ('company', 'ngo', 'school', 'university', 'other');
          END IF;
        END
        $$
        """
    )
    op.execute("ALTER TABLE accounts ADD COLUMN kind account_kind NOT NULL DEFAULT 'company'")
    _create_rls("up")
    _regrant(ALL_NEW_TABLES)


def downgrade() -> None:
    _drop_policies(ALL_NEW_TABLES)
    op.execute("ALTER TABLE accounts DROP COLUMN kind")
    op.execute("DROP TYPE IF EXISTS account_kind")
    for table in UNIT_COLUMN_TABLES:
        op.alter_column(table, "unit_id", new_column_name="establishment_id")
    for table in ACCOUNT_COLUMN_TABLES:
        op.alter_column(table, "account_id", new_column_name="company_id")
    for old, new in reversed(TABLE_RENAMES):
        op.rename_table(new, old)
    old_tables = tuple(_old(t) for t in ALL_NEW_TABLES)
    _rename_constraints_and_indexes(old_tables, "down")
    _create_rls("down")
    _regrant(old_tables)
