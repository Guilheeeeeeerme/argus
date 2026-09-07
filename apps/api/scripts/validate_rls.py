#!/usr/bin/env python3
"""Validate Row-Level Security tenant isolation on local PostgreSQL.

Usage (from backend/):
    PYTHONPATH=src python scripts/validate_rls.py

Requires DATABASE_URL (argus_app) and ADMIN_DATABASE_URL (argus superuser for seeding).
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://argus_app:argus_app@postgres:5432/argus",
)
ADMIN_DATABASE_URL = os.getenv(
    "ADMIN_DATABASE_URL",
    "postgresql+asyncpg://argus:argus@postgres:5432/argus",
)


async def _set_config(conn, key: str, value: str) -> None:
    await conn.execute(
        text("SELECT set_config(:key, :value, true)"),
        {"key": key, "value": value},
    )


async def main() -> int:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    admin_engine = create_async_engine(ADMIN_DATABASE_URL)
    app_engine = create_async_engine(DATABASE_URL)

    async with admin_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO companies (id, name, slug) VALUES "
                "(:id_a, 'Company A', :slug_a), (:id_b, 'Company B', :slug_b)"
            ),
            {
                "id_a": tenant_a,
                "id_b": tenant_b,
                "slug_a": f"tenant-a-{tenant_a.hex[:8]}",
                "slug_b": f"tenant-b-{tenant_b.hex[:8]}",
            },
        )
        await conn.execute(
            text(
                "INSERT INTO locations (id, company_id, name) VALUES "
                "(:id_a, :tenant_a, 'Location A'), (:id_b, :tenant_b, 'Location B')"
            ),
            {
                "id_a": uuid.uuid4(),
                "id_b": uuid.uuid4(),
                "tenant_a": tenant_a,
                "tenant_b": tenant_b,
            },
        )

    async with app_engine.connect() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM locations"))
        count_without_context = result.scalar_one()
    if count_without_context != 0:
        print(f"FAIL: expected 0 locations without tenant context, got {count_without_context}")
        return 1
    print("PASS: no tenant context → 0 rows visible")

    async with app_engine.connect() as conn:
        async with conn.begin():
            await _set_config(conn, "app.current_company_id", str(tenant_a))
            result = await conn.execute(
                text("SELECT COUNT(*) FROM locations WHERE company_id = :tid"),
                {"tid": tenant_b},
            )
            cross_count = result.scalar_one()
    if cross_count != 0:
        print(f"FAIL: tenant A context should not see tenant B rows, got {cross_count}")
        return 1
    print("PASS: tenant A context → cannot read tenant B rows")

    async with app_engine.connect() as conn:
        async with conn.begin():
            await _set_config(conn, "app.current_company_id", str(tenant_a))
            result = await conn.execute(text("SELECT COUNT(*) FROM locations"))
            own_count = result.scalar_one()
    if own_count != 1:
        print(f"FAIL: tenant A should see exactly 1 market, got {own_count}")
        return 1
    print("PASS: tenant A context → 1 own row visible")

    async with app_engine.connect() as conn:
        async with conn.begin():
            await _set_config(conn, "app.current_role", "root")
            result = await conn.execute(text("SELECT COUNT(*) FROM locations"))
            admin_count = result.scalar_one()
    if admin_count < 2:
        print(f"FAIL: root should see all locations, got {admin_count}")
        return 1
    print(f"PASS: root → {admin_count} rows visible")

    await app_engine.dispose()
    await admin_engine.dispose()
    print("\nRLS validation succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
