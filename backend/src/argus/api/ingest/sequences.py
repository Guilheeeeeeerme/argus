"""POST /v1/ingest/sequences — edge frame sequence ingestion."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from argus.core.auth import EdgeAuthContext, get_edge_auth_context
from argus.domain.schemas.ingest import IngestAcceptedResponse, IngestSequenceRequest
from argus.services.ingestion import IngestionService

router = APIRouter(tags=["ingest"])

_service = IngestionService()


@router.post(
    "/ingest/sequences",
    response_model=IngestAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def ingest_sequence(
    body: IngestSequenceRequest,
    auth: EdgeAuthContext = Depends(get_edge_auth_context),
) -> IngestAcceptedResponse | JSONResponse:
    result = await _service.accept_sequence(auth, body)
    if result.status == "duplicate":
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=result.model_dump(mode="json"),
        )
    return result
