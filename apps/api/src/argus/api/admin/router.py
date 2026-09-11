"""Admin API router aggregation."""

from fastapi import APIRouter

from argus.api.admin import (
    cameras,
    companies,
    establishments,
    prompt_sets,
    webhooks,
)

router = APIRouter(prefix="/v1")
router.include_router(companies.router)
router.include_router(establishments.router)
router.include_router(cameras.router)
router.include_router(prompt_sets.router)
router.include_router(webhooks.router)
