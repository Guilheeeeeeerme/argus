"""api-ingest FastAPI router."""

from __future__ import annotations

from fastapi import APIRouter

from argus.api.ingest.sequences import router as sequences_router

router = APIRouter(prefix="/v1")
router.include_router(sequences_router)


@router.get("/ingest/health")
async def ingest_health() -> dict[str, str]:
    return {"status": "ok"}
