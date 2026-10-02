"""014_rename_accounts_units round-trip against a disposable Postgres (ARGUS_MIGRATION_TEST_URL)."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest

TEST_URL = os.getenv("ARGUS_MIGRATION_TEST_URL")
pytestmark = pytest.mark.skipif(not TEST_URL, reason="requires disposable Postgres")
API = Path(__file__).resolve().parents[1]


def _alembic(url: str, *args: str) -> None:
    environment = os.environ | {
        "ADMIN_DATABASE_URL": url.replace("postgresql://", "postgresql+asyncpg://", 1),
        "DATABASE_URL": url.replace("postgresql://", "postgresql+asyncpg://", 1),
        "PYTHONPATH": str(API / "src"),
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=API, env=environment, check=False, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


async def _snapshot(url: str) -> dict:
    conn = await asyncpg.connect(url)
    try:
        tables = {r["table_name"] for r in await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )}
        columns = {(r["table_name"], r["column_name"]) for r in await conn.fetch(
            "SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'public'"
        )}
        policies = {(r["tablename"], r["policyname"]): (r["qual"] or "") + (r["with_check"] or "")
                    for r in await conn.fetch("SELECT tablename, policyname, qual, with_check FROM pg_policies WHERE schemaname = 'public'")}
        constraints = {r["conname"] for r in await conn.fetch(
            "SELECT conname FROM pg_constraint WHERE connamespace = 'public'::regnamespace"
        )}
        indexes = {r["indexname"] for r in await conn.fetch(
            "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
        )}
        version = await conn.fetchval("SELECT version_num FROM alembic_version")
        kind_default = await conn.fetchval(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'accounts' AND column_name = 'kind'"
        )
        enums = {r["typname"] for r in await conn.fetch("SELECT typname FROM pg_type WHERE typtype = 'e'")}
        return {
            "tables": tables, "columns": columns, "policies": policies, "constraints": constraints,
            "indexes": indexes, "version": version, "kind_default": kind_default, "enums": enums,
        }
    finally:
        await conn.close()


def test_rename_round_trip():
    database = "argus_rename_test_" + uuid4().hex

    async def prepare() -> str:
        conn = await asyncpg.connect(TEST_URL)
        try:
            await conn.execute(f'CREATE DATABASE "{database}"')
            if not await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = 'argus_app'"):
                await conn.execute("CREATE ROLE argus_app NOBYPASSRLS")
        finally:
            await conn.close()
        from urllib.parse import urlsplit, urlunsplit

        return urlunsplit(urlsplit(TEST_URL)._replace(path="/" + database))

    async def cleanup() -> None:
        conn = await asyncpg.connect(TEST_URL)
        try:
            await conn.execute(f'DROP DATABASE "{database}" WITH (FORCE)')
        finally:
            await conn.close()

    url = asyncio.run(prepare())
    try:
        _alembic(url, "upgrade", "head")
        after = asyncio.run(_snapshot(url))
        assert after["version"] == "014_rename_accounts_units"
        assert {"accounts", "account_users", "account_user_memberships", "units"} <= after["tables"]
        assert not {"companies", "company_users", "company_user_memberships", "establishments"} & after["tables"]
        assert ("cameras", "account_id") in after["columns"] and ("cameras", "unit_id") in after["columns"]
        assert ("cameras", "company_id") not in after["columns"]
        assert ("account_users", "account_id") in after["columns"]
        assert ("accounts", "kind") in after["columns"]
        assert after["kind_default"] == "'company'::account_kind"
        assert "account_kind" in after["enums"]
        assert "fk_cameras_unit_id_units" in after["constraints"]
        assert "accounts_pkey" in after["constraints"] and "uq_account_users_email" in after["constraints"]
        assert "ix_units_account_id" in after["indexes"] and "ix_cameras_unit_id" in after["indexes"]
        assert not any("compan" in n or "establishment" in n for n in after["constraints"] | after["indexes"])
        assert "app.current_account_id" in after["policies"][("units", "tenant_isolation_select")]
        assert "app.current_account_id" in after["policies"][("accounts", "tenant_isolation_update")]
        assert ("account_user_memberships", "platform_all") in after["policies"]
        assert not any("app.current_company_id" in v for v in after["policies"].values())

        _alembic(url, "downgrade", "013_public_app_grants")
        before = asyncio.run(_snapshot(url))
        assert before["version"] == "013_public_app_grants"
        assert {"companies", "company_users", "company_user_memberships", "establishments"} <= before["tables"]
        assert not {"accounts", "units"} & before["tables"]
        assert ("cameras", "company_id") in before["columns"] and ("cameras", "establishment_id") in before["columns"]
        assert ("companies", "kind") not in before["columns"]
        assert "account_kind" not in before["enums"]
        assert "fk_cameras_establishment_id_establishments" in before["constraints"]
        assert "ix_establishments_company_id" in before["indexes"]
        assert not any("account" in n or "unit" in n for n in before["constraints"] | before["indexes"])
        assert "app.current_company_id" in before["policies"][("establishments", "tenant_isolation_select")]
        assert not any("app.current_account_id" in v for v in before["policies"].values())

        _alembic(url, "upgrade", "head")
        again = asyncio.run(_snapshot(url))
        assert again["version"] == "014_rename_accounts_units"
        assert again["constraints"] == after["constraints"]
        assert again["indexes"] == after["indexes"]
        assert set(again["policies"]) == set(after["policies"])
    finally:
        asyncio.run(cleanup())
