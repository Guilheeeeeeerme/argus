#!/usr/bin/env python3
"""Verify PR-3: DB, Redis, S3, JWT auth context, and RLS session variables."""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

os.environ.setdefault("AUTH0_USE_MOCK", "true")

from sqlalchemy import select, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from argus.config import get_settings  # noqa: E402

get_settings.cache_clear()
settings = get_settings()

from argus.core.auth import _auth_context_from_token  # noqa: E402
from argus.domain.enums import UserRole  # noqa: E402
from argus.domain.models import Tenant  # noqa: E402
from argus.integrations.auth0 import create_mock_token  # noqa: E402
from argus.services.database import (  # noqa: E402
    get_session_factory,
    set_session_context,
    tenant_session,
)
from argus.services.redis import ping, set_key, get_key  # noqa: E402
from argus.services.storage import (  # noqa: E402
    ensure_bucket_exists,
    generate_presigned_get_url,
    upload_bytes,
)


SEED_TENANT_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
OTHER_TENANT_ID = uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")


async def verify_database() -> None:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
    print("OK database SELECT 1")


async def verify_redis() -> None:
    assert await ping()
    await set_key("argus:verify:pr3", "ok", ex=60)
    assert await get_key("argus:verify:pr3") == "ok"
    print("OK redis ping + kv")


async def verify_storage() -> None:
    await ensure_bucket_exists()
    key = "test/verify-pr3.txt"
    uri = await upload_bytes(key, b"argus-pr3", content_type="text/plain")
    assert uri.startswith("s3://")
    url = await generate_presigned_get_url(key, expires_in=300)
    assert "http" in url
    print("OK s3 upload + presigned url")


async def verify_jwt_and_rls() -> None:
    token = create_mock_token(
        sub="auth0|seed-tenant-admin",
        tenant_id=str(SEED_TENANT_ID),
        role=UserRole.TENANT_ADMIN.value,
    )
    auth = _auth_context_from_token(token)
    assert auth.tenant_id == SEED_TENANT_ID
    assert auth.role == UserRole.TENANT_ADMIN
    print("OK jwt decode tenant_admin")

    watcher_token = create_mock_token(
        sub="auth0|watcher",
        tenant_id=str(SEED_TENANT_ID),
        role=UserRole.WATCHER.value,
    )
    watcher = _auth_context_from_token(watcher_token)
    assert watcher.role == UserRole.WATCHER
    print("OK jwt decode watcher")

    async with tenant_session(SEED_TENANT_ID, UserRole.TENANT_ADMIN.value) as session:
        tenant = await session.scalar(
            select(Tenant).where(Tenant.id == SEED_TENANT_ID)
        )
        assert tenant is not None

        await set_session_context(session, tenant_id=OTHER_TENANT_ID, role=UserRole.TENANT_ADMIN.value)
        blocked = await session.scalar(
            select(Tenant).where(Tenant.id == SEED_TENANT_ID)
        )
        assert blocked is None
    print("OK rls tenant isolation via set_config")


async def main() -> int:
  checks = [
      verify_database,
      verify_redis,
      verify_storage,
      verify_jwt_and_rls,
  ]
  for check in checks:
      await check()
  print("ALL PR-3 CHECKS PASSED")
  return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
