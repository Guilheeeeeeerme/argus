"""Shared test helpers: Redis-backed session tokens."""

from __future__ import annotations

import uuid

from argus.domain.enums import UserRole
from argus.services.sessions import SessionData, create_session


async def session_token(
    role: UserRole,
    company_id: str | None = None,
    establishment_id: str | None = None,
    location_id: str | None = None,
    user_id: str | None = None,
) -> str:
    """Create a session. ``location_id`` is accepted as an alias for establishment."""
    est = establishment_id or location_id
    return await create_session(
        SessionData(
            user_id=user_id or str(uuid.uuid5(uuid.NAMESPACE_DNS, f"test-{role.value}")),
            email=f"{role.value}@test.local",
            role=role.value,
            company_id=company_id,
            establishment_id=est,
            location_id=est,
        )
    )


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
