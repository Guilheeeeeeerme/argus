"""MVP domain schema: establishments, prompts, detections, triage, webhooks.

Revision ID: 010_mvp_domain
Revises: 009_notify_hitl
Create Date: 2026-09-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010_mvp_domain"
down_revision: Union[str, None] = "009_notify_hitl"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables removed by this migration (RLS must be disabled first)
DROP_TABLES = [
    "notification_deliveries",
    "notification_configs",
    "feedback",
    "decision_evidences",
    "decisions",
    "evidences",
    "rule_region_mappings",
    "rules",
    "recipes",
    "rule_set_camera_assignments",
    "rule_set_schedules",
    "rule_sets",
    "regions_of_interest",
    "agent_locations",
    "agents",
]

# New tenant-scoped tables (plus cameras/audit_records already had RLS)
NEW_TENANT_TABLES = [
    "establishments",
    "prompt_sets",
    "prompts",
    "detections",
    "triage_cases",
    "feedback",
    "webhook_endpoints",
    "context_events",
]

feedback_disposition = postgresql.ENUM(
    "true_positive",
    "false_positive",
    "false_negative",
    name="feedback_disposition",
    create_type=False,
)
triage_case_state = postgresql.ENUM(
    "open",
    "confirmed",
    "dismissed",
    "false_positive",
    name="triage_case_state",
    create_type=False,
)


def _disable_tenant_rls(table: str) -> None:
    for policy in (
        "platform_all",
        "tenant_isolation_delete",
        "tenant_isolation_update",
        "tenant_isolation_insert",
        "tenant_isolation_select",
    ):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
    op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


def _enable_tenant_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_select ON {table}
            FOR SELECT
            USING (
                company_id = NULLIF(current_setting('app.current_company_id', true), '')::uuid
            )
        """
    )
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_insert ON {table}
            FOR INSERT
            WITH CHECK (
                company_id = NULLIF(current_setting('app.current_company_id', true), '')::uuid
            )
        """
    )
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_update ON {table}
            FOR UPDATE
            USING (
                company_id = NULLIF(current_setting('app.current_company_id', true), '')::uuid
            )
            WITH CHECK (
                company_id = NULLIF(current_setting('app.current_company_id', true), '')::uuid
            )
        """
    )
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_delete ON {table}
            FOR DELETE
            USING (
                company_id = NULLIF(current_setting('app.current_company_id', true), '')::uuid
            )
        """
    )
    op.execute(
        f"""
        CREATE POLICY platform_all ON {table}
            FOR ALL
            USING (current_setting('app.current_role', true) IN ('root', 'admin'))
            WITH CHECK (current_setting('app.current_role', true) IN ('root', 'admin'))
        """
    )


def upgrade() -> None:
    # --- Enum for triage states ---
    op.execute(
        "CREATE TYPE triage_case_state AS ENUM ("
        "'open', 'confirmed', 'dismissed', 'false_positive')"
    )

    # --- Establishments (migrate from locations) ---
    op.create_table(
        "establishments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("timezone", sa.String(63), nullable=False, server_default="UTC"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_establishments_company_id", "establishments", ["company_id"])

    op.execute(
        """
        INSERT INTO establishments (id, company_id, name, address, timezone, active, created_at)
        SELECT
            id,
            company_id,
            name,
            address,
            timezone,
            (deleted_at IS NULL),
            created_at
        FROM locations
        """
    )

    # --- Cameras: location_id → establishment_id; drop placement ---
    op.add_column(
        "cameras",
        sa.Column("establishment_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute("UPDATE cameras SET establishment_id = location_id")
    op.alter_column("cameras", "establishment_id", nullable=False)
    op.create_foreign_key(
        "fk_cameras_establishment_id_establishments",
        "cameras",
        "establishments",
        ["establishment_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_cameras_establishment_id", "cameras", ["establishment_id"])

    op.drop_constraint("cameras_location_id_fkey", "cameras", type_="foreignkey")
    op.drop_column("cameras", "location_id")
    op.drop_column("cameras", "placement_x")
    op.drop_column("cameras", "placement_y")

    # --- Drop RLS + old dependent tables (feedback recreated below) ---
    # audit_records kept but decision_id dropped after decisions gone
    for table in DROP_TABLES + ["locations", "audit_records"]:
        _disable_tenant_rls(table)

    # Drop audit FK to decisions before dropping decisions
    op.drop_constraint("audit_records_decision_id_fkey", "audit_records", type_="foreignkey")
    op.drop_column("audit_records", "decision_id")

    for table in DROP_TABLES:
        op.drop_table(table)

    op.drop_table("locations")

    # --- New MVP tables ---
    op.create_table(
        "prompt_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cameras.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_prompt_sets_company_id", "prompt_sets", ["company_id"])
    op.create_index("ix_prompt_sets_camera_id", "prompt_sets", ["camera_id"])

    op.create_table(
        "prompts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prompt_set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("prompt_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_prompts_company_id", "prompts", ["company_id"])
    op.create_index("ix_prompts_prompt_set_id", "prompts", ["prompt_set_id"])

    op.create_table(
        "detections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cameras.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "establishment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("establishments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence_id", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("prompt_hits", postgresql.JSONB(), nullable=False),
        sa.Column("clip_uri", sa.Text(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frame_uris", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_detections_company_id", "detections", ["company_id"])
    op.create_index("ix_detections_camera_id", "detections", ["camera_id"])
    op.create_index("ix_detections_establishment_id", "detections", ["establishment_id"])

    op.create_table(
        "triage_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "detection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detections.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("state", triage_case_state, nullable=False, server_default="open"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_triage_cases_company_id", "triage_cases", ["company_id"])

    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "triage_case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("triage_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("disposition", feedback_disposition, nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # pgvector type (extension already enabled in 006)
    op.execute("ALTER TABLE feedback ADD COLUMN embedding vector(1536)")
    op.create_index("ix_feedback_company_id", "feedback", ["company_id"])
    op.create_index("ix_feedback_triage_case_id", "feedback", ["triage_case_id"])

    op.create_table(
        "webhook_endpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "establishment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("establishments.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_webhook_endpoints_company_id", "webhook_endpoints", ["company_id"])
    op.create_index(
        "ix_webhook_endpoints_establishment_id", "webhook_endpoints", ["establishment_id"]
    )

    op.create_table(
        "context_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "webhook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("webhook_endpoints.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "establishment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("establishments.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cameras.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(63), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_context_events_company_id", "context_events", ["company_id"])
    op.create_index("ix_context_events_webhook_id", "context_events", ["webhook_id"])
    op.create_index(
        "ix_context_events_establishment_id", "context_events", ["establishment_id"]
    )
    op.create_index("ix_context_events_camera_id", "context_events", ["camera_id"])

    # audit_records: optional triage_case_id
    op.add_column(
        "audit_records",
        sa.Column("triage_case_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_audit_records_triage_case_id_triage_cases",
        "audit_records",
        "triage_cases",
        ["triage_case_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_audit_records_triage_case_id", "audit_records", ["triage_case_id"])

    # --- RLS for new + retained tenant tables ---
    for table in NEW_TENANT_TABLES + ["audit_records"]:
        _enable_tenant_rls(table)

    # cameras already had RLS from 007; policies remain valid (company_id unchanged)


def downgrade() -> None:
    for table in reversed(NEW_TENANT_TABLES + ["audit_records"]):
        _disable_tenant_rls(table)

    op.drop_constraint(
        "fk_audit_records_triage_case_id_triage_cases", "audit_records", type_="foreignkey"
    )
    op.drop_index("ix_audit_records_triage_case_id", table_name="audit_records")
    op.drop_column("audit_records", "triage_case_id")

    op.drop_table("context_events")
    op.drop_table("webhook_endpoints")
    op.drop_table("feedback")
    op.drop_table("triage_cases")
    op.drop_table("detections")
    op.drop_table("prompts")
    op.drop_table("prompt_sets")

    # Restore locations and camera.location_id (data loss for new tables accepted)
    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("sketch", sa.Text(), nullable=True),
        sa.Column("timezone", sa.String(63), nullable=False, server_default="UTC"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_locations_company_id", "locations", ["company_id"])
    op.execute(
        """
        INSERT INTO locations (id, company_id, name, address, timezone, created_at, deleted_at)
        SELECT
            id,
            company_id,
            name,
            address,
            timezone,
            created_at,
            CASE WHEN active THEN NULL ELSE now() END
        FROM establishments
        """
    )

    op.add_column(
        "cameras",
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("cameras", sa.Column("placement_x", sa.Float(), nullable=True))
    op.add_column("cameras", sa.Column("placement_y", sa.Float(), nullable=True))
    op.execute("UPDATE cameras SET location_id = establishment_id")
    op.alter_column("cameras", "location_id", nullable=False)
    op.create_foreign_key(
        "cameras_location_id_fkey",
        "cameras",
        "locations",
        ["location_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "fk_cameras_establishment_id_establishments", "cameras", type_="foreignkey"
    )
    op.drop_index("ix_cameras_establishment_id", table_name="cameras")
    op.drop_column("cameras", "establishment_id")

    op.drop_table("establishments")

    op.add_column(
        "audit_records",
        sa.Column("decision_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.execute("DROP TYPE IF EXISTS triage_case_state")

    # Downgrade does not recreate dropped retail tables (agents, rules, evidences, …).
