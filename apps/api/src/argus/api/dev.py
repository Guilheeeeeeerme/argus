"""Development-only helpers for the local smoke test."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from argus.config import settings
from argus.domain.enums import UserRole
from argus.domain.models import CompanyUser
from argus.integrations.auth0 import create_mock_m2m_token
from argus.services.database import get_db, set_session_context
from argus.services.sessions import SessionData, create_session

router = APIRouter(prefix="/v1/dev", tags=["development"])

DEMO_COMPANY_ID = "11111111-1111-4111-8111-111111111111"
DEMO_CAMERA_ID = "33333333-3333-4333-8333-333333333333"

_PERSONA_ROLES = {
    "root": UserRole.ROOT,
    "admin": UserRole.ADMIN,
    "manager": UserRole.MANAGER,
    "operator": UserRole.OPERATOR,
}


@router.get("/session/{persona}")
async def create_dev_session(persona: str) -> dict[str, str | None]:
    """Create a Redis session for a seeded user; disabled outside mock auth."""
    if not settings.auth0_use_mock:
        raise HTTPException(status_code=404, detail="Development auth is disabled")

    role = _PERSONA_ROLES.get(persona)
    if role is not None:
        async for session in get_db():
            await set_session_context(session, company_id=None, role=UserRole.ROOT.value)
            user = await session.scalar(
                select(CompanyUser).where(CompanyUser.role == role).order_by(CompanyUser.email)
            )
        if user is None:
            raise HTTPException(status_code=404, detail="No seeded user for persona; run seed")
        data = SessionData(
            user_id=str(user.id),
            email=user.email,
            role=user.role.value,
            company_id=str(user.company_id) if user.company_id else None,
        )
        token = await create_session(data)
        return {
            "persona": persona,
            "role": user.role.value,
            "company_id": str(user.company_id) if user.company_id else None,
            "token": token,
        }

    if persona == "edge":
        token = create_mock_m2m_token(
            sub="edge-device-demo-001@clients",
            company_id=DEMO_COMPANY_ID,
            camera_id=DEMO_CAMERA_ID,
        )
        return {"persona": persona, "role": "edge", "company_id": DEMO_COMPANY_ID, "token": token}
    raise HTTPException(status_code=404, detail="Unknown development persona")
