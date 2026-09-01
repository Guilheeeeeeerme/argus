"""Triage REST router."""

from fastapi import APIRouter

from argus.api.triage.decisions import router as decisions_router

router = APIRouter(prefix="/v1")
router.include_router(decisions_router)
