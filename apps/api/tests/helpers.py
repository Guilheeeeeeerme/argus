"""Shared test helpers: Redis-backed session tokens."""

from __future__ import annotations

import uuid

from sqlalchemy.dialects.postgresql import insert

from argus.domain.enums import PLATFORM_ROLES, UserRole
from argus.domain.models import CompanyUser, CompanyUserMembership
from argus.services.database import company_session
from argus.services.sessions import SessionData, create_session


async def session_token(
    role: UserRole,
    company_id: str | None = None,
    establishment_id: str | None = None,
    location_id: str | None = None,
    user_id: str | None = None,
) -> str:
    """Create a session. ``location_id`` is accepted as an alias for establishment."""
    actual_user_id = user_id or str(uuid.uuid5(uuid.NAMESPACE_DNS, f"test-{role.value}"))
    if role not in PLATFORM_ROLES and company_id:
        async with company_session(None, UserRole.ROOT.value) as db:
            await db.execute(insert(CompanyUser).values(
                id=uuid.UUID(actual_user_id), email=f"{role.value}@test.local", role=role,
                company_id=uuid.UUID(company_id),
            ).on_conflict_do_nothing(index_elements=["id"]))
            await db.execute(insert(CompanyUserMembership).values(
                user_id=uuid.UUID(actual_user_id), company_id=uuid.UUID(company_id),
            ).on_conflict_do_nothing())
    est = establishment_id or location_id
    return await create_session(
        SessionData(
            user_id=actual_user_id,
            email=f"{role.value}@test.local",
            role=role.value,
            company_id=company_id,
            establishment_id=est,
            location_id=est,
        )
    )


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
