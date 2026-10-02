"""Shared test helpers: Redis-backed session tokens."""

from __future__ import annotations

import uuid

from sqlalchemy.dialects.postgresql import insert

from argus.domain.enums import PLATFORM_ROLES, UserRole
from argus.domain.models import AccountUser, AccountUserMembership
from argus.services.database import account_session
from argus.services.sessions import SessionData, create_session


async def session_token(
    role: UserRole,
    account_id: str | None = None,
    unit_id: str | None = None,
    user_id: str | None = None,
) -> str:
    """Create a session for ``role`` (membership row seeded for non-platform roles)."""
    actual_user_id = user_id or str(uuid.uuid5(uuid.NAMESPACE_DNS, f"test-{role.value}"))
    if role not in PLATFORM_ROLES and account_id:
        async with account_session(None, UserRole.ROOT.value) as db:
            await db.execute(insert(AccountUser).values(
                id=uuid.UUID(actual_user_id), email=f"{role.value}@test.local", role=role,
                account_id=uuid.UUID(account_id),
            ).on_conflict_do_nothing(index_elements=["id"]))
            await db.execute(insert(AccountUserMembership).values(
                user_id=uuid.UUID(actual_user_id), account_id=uuid.UUID(account_id),
            ).on_conflict_do_nothing())
    est = unit_id
    return await create_session(
        SessionData(
            user_id=actual_user_id,
            email=f"{role.value}@test.local",
            role=role.value,
            account_id=account_id,
            unit_id=est,
        )
    )


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
