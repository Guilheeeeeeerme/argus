"""Development-only helpers for the local mock smoke test."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from argus.config import settings
from argus.domain.enums import UserRole
from argus.integrations.auth0 import create_mock_m2m_token, create_mock_token

router = APIRouter(prefix="/v1/dev", tags=["development"])

DEMO_TENANT_ID = "11111111-1111-4111-8111-111111111111"
DEMO_CAMERA_ID = "33333333-3333-4333-8333-333333333333"


@router.get("/session/{persona}")
async def create_dev_session(persona: str) -> dict[str, str | None]:
    """Issue a predictable local token; this route is disabled outside mock auth."""
    if not settings.auth0_use_mock:
        raise HTTPException(status_code=404, detail="Development auth is disabled")

    if persona == "root":
        token = create_mock_token(
            sub="auth0|seed-root-admin", tenant_id="", role=UserRole.ROOT_ADMIN.value
        )
        return {"persona": persona, "role": UserRole.ROOT_ADMIN.value, "tenant_id": None, "token": token}
    if persona == "admin":
        token = create_mock_token(
            sub="auth0|seed-tenant-admin",
            tenant_id=DEMO_TENANT_ID,
            role=UserRole.TENANT_ADMIN.value,
        )
        return {"persona": persona, "role": UserRole.TENANT_ADMIN.value, "tenant_id": DEMO_TENANT_ID, "token": token}
    if persona == "watcher":
        token = create_mock_token(
            sub="auth0|seed-watcher",
            tenant_id=DEMO_TENANT_ID,
            role=UserRole.WATCHER.value,
        )
        return {"persona": persona, "role": UserRole.WATCHER.value, "tenant_id": DEMO_TENANT_ID, "token": token}
    if persona == "edge":
        token = create_mock_m2m_token(
            sub="edge-device-demo-001@clients",
            tenant_id=DEMO_TENANT_ID,
            camera_id=DEMO_CAMERA_ID,
        )
        return {"persona": persona, "role": "edge", "tenant_id": DEMO_TENANT_ID, "token": token}
    raise HTTPException(status_code=404, detail="Unknown development persona")
