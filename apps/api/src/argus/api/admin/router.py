"""Admin API router aggregation."""

from fastapi import APIRouter

from argus.api.admin import (
    cameras,
    rule_sets,
    locations,
    notifications,
    rules,
    companies,
)

router = APIRouter(prefix="/v1")
router.include_router(companies.router)
router.include_router(locations.router)
router.include_router(cameras.router)
router.include_router(rule_sets.router)
router.include_router(rules.router)
router.include_router(notifications.router)
