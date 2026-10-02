"""Commit regression against an explicitly supplied disposable Postgres server."""

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


def test_grant_upgrade_commits_revision_and_permissions():
    database = "argus_migration_test_" + uuid4().hex

    async def prepare():
        connection = await asyncpg.connect(TEST_URL)
        try:
            await connection.execute(f'CREATE DATABASE "{database}"')
            if not await connection.fetchval(
                "SELECT 1 FROM pg_roles WHERE rolname='argus_app'"
            ):
                await connection.execute("CREATE ROLE argus_app NOBYPASSRLS")
        finally:
            await connection.close()
        from urllib.parse import urlsplit, urlunsplit

        parsed = urlsplit(TEST_URL)
        database_url = urlunsplit(parsed._replace(path="/" + database))
        connection = await asyncpg.connect(database_url)
        try:
            await connection.execute(
                "CREATE SCHEMA argus; CREATE TABLE argus.alembic_version (version_num varchar(32) PRIMARY KEY); INSERT INTO argus.alembic_version VALUES ('010_mvp_domain'); CREATE TABLE argus.commit_probe (id int); INSERT INTO argus.commit_probe VALUES (42)"
            )
        finally:
            await connection.close()
        return database_url

    async def verify(url):
        connection = await asyncpg.connect(url)
        try:
            return (
                await connection.fetchval(
                    "SELECT version_num FROM argus.alembic_version"
                ),
                await connection.fetchval(
                    "SELECT has_table_privilege('argus_app','argus.commit_probe','SELECT')"
                ),
                await connection.fetchval("SELECT count(*) FROM argus.commit_probe"),
            )
        finally:
            await connection.close()

    async def cleanup():
        connection = await asyncpg.connect(TEST_URL)
        try:
            await connection.execute(f'DROP DATABASE "{database}"')
        finally:
            await connection.close()

    url = asyncio.run(prepare())
    try:
        environment = os.environ | {
            "ADMIN_DATABASE_URL": url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            ),
            "PYTHONPATH": str(API / "src"),
        }
        for _ in range(2):
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=API,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, result.stderr
            assert asyncio.run(verify(url)) == ("011_argus_schema_grants", True, 1)
    finally:
        asyncio.run(cleanup())
