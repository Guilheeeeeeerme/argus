"""Admin API router aggregation."""

from fastapi import APIRouter

from argus.api.admin import (
    cameras,
    context_modes,
    markets,
    notifications,
    rules,
    tenants,
)

router = APIRouter(prefix="/v1")
router.include_router(tenants.router)
router.include_router(markets.router)
router.include_router(cameras.router)
router.include_router(context_modes.router)
router.include_router(rules.router)
router.include_router(notifications.router)
