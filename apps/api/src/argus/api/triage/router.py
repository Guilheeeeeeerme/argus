"""Triage REST router."""

from fastapi import APIRouter

from argus.api.triage.cameras import router as cameras_router
from argus.api.triage.triage_cases import router as triage_cases_router

router = APIRouter(prefix="/v1")
router.include_router(triage_cases_router)
router.include_router(cameras_router)
