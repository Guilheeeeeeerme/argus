"""Admin API router aggregation."""

from fastapi import APIRouter

from argus.api.admin import (
    accounts,
    cameras,
    units,
    prompt_sets,
    webhooks,
)

router = APIRouter(prefix="/v1")
router.include_router(accounts.router)
router.include_router(units.router)
router.include_router(cameras.router)
router.include_router(prompt_sets.router)
router.include_router(webhooks.router)
