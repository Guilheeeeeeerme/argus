"""Validate tenant isolation (RLS) for the Account/Unit schema.

Requires DATABASE_URL (argus_app, NOBYPASSRLS) and ADMIN_DATABASE_URL (owner, used
to seed two throwaway accounts). Exit code 0 when every check passes.

    PYTHONPATH=src python3 scripts/validate_rls.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

APP_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://argus_app:argus_app@postgres:5432/argus")
ADMIN_URL = os.getenv("ADMIN_DATABASE_URL", "postgresql+asyncpg://argus:argus@postgres:5432/argus")

GUC_ACCOUNT = "app.current_account_id"
GUC_ROLE = "app.current_role"


async def _set(conn, account_id: str | None, role: str) -> None:
    await conn.execute(text(f"SELECT set_config('{GUC_ACCOUNT}', :a, true)"), {"a": account_id or ""})
    await conn.execute(text(f"SELECT set_config('{GUC_ROLE}', :r, true)"), {"r": role})


async def main() -> int:
    failures: list[str] = []
    admin = create_async_engine(ADMIN_URL, connect_args={"statement_cache_size": 0})
    app = create_async_engine(APP_URL, connect_args={"statement_cache_size": 0})
    suffix = uuid.uuid4().hex[:8]
    account_a, account_b = uuid.uuid4(), uuid.uuid4()
    unit_a, unit_b = uuid.uuid4(), uuid.uuid4()

    try:
        async with admin.begin() as conn:
            await _set(conn, None, "root")
            await conn.execute(
                text(
                    "INSERT INTO accounts (id, name, slug) VALUES "
                    "(:a, 'RLS A', :sa), (:b, 'RLS B', :sb)"
                ),
                {"a": account_a, "sa": f"rls-a-{suffix}", "b": account_b, "sb": f"rls-b-{suffix}"},
            )
            await conn.execute(
                text(
                    "INSERT INTO units (id, account_id, name) VALUES "
                    "(:ua, :a, 'Unit A'), (:ub, :b, 'Unit B')"
                ),
                {"ua": unit_a, "a": account_a, "ub": unit_b, "b": account_b},
            )

        async with app.connect() as conn:
            # 1. No context → nothing visible.
            await _set(conn, None, "operator")
            count = await conn.scalar(text("SELECT count(*) FROM units WHERE id IN (:ua, :ub)"), {"ua": unit_a, "ub": unit_b})
            if count != 0:
                failures.append(f"no-context: expected 0 units, got {count}")

            # 2. Account A sees only its unit.
            await _set(conn, str(account_a), "manager")
            rows = (await conn.execute(text("SELECT id FROM units WHERE id IN (:ua, :ub)"), {"ua": unit_a, "ub": unit_b})).scalars().all()
            if set(rows) != {unit_a}:
                failures.append(f"account A: expected only {unit_a}, got {rows}")
            visible_accounts = (await conn.execute(text("SELECT id FROM accounts WHERE id IN (:a, :b)"), {"a": account_a, "b": account_b})).scalars().all()
            if set(visible_accounts) != {account_a}:
                failures.append(f"account A: accounts visible {visible_accounts}")

            # 3. Cross-tenant insert is rejected.
            await conn.execute(text("SAVEPOINT cross_insert"))
            try:
                await conn.execute(
                    text("INSERT INTO units (id, account_id, name) VALUES (:id, :b, 'Intruder')"),
                    {"id": uuid.uuid4(), "b": account_b},
                )
                failures.append("account A could insert a unit into account B")
            except Exception:
                await conn.execute(text("ROLLBACK TO SAVEPOINT cross_insert"))

            # 4. Platform role sees both.
            await _set(conn, None, "root")
            count = await conn.scalar(text("SELECT count(*) FROM units WHERE id IN (:ua, :ub)"), {"ua": unit_a, "ub": unit_b})
            if count != 2:
                failures.append(f"root: expected 2 units, got {count}")
            await conn.rollback()
    finally:
        async with admin.begin() as conn:
            await _set(conn, None, "root")
            await conn.execute(text("DELETE FROM accounts WHERE id IN (:a, :b)"), {"a": account_a, "b": account_b})
        await app.dispose()
        await admin.dispose()

    for failure in failures:
        print(f"FAIL: {failure}")
    print("RLS validation " + ("FAILED" if failures else "OK"))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
