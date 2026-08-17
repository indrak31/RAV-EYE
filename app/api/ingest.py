"""POST /api/ingest — fully working ingestion endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.case import IngestRequest, IngestResponse
from app.services.ingest import ingest

router = APIRouter(prefix="/api", tags=["ingest"])


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_case(
    payload: IngestRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> IngestResponse:
    case, replayed = ingest(db, payload)
    if replayed:
        # Idempotent replay -> 200 with `replayed: true` per api-contract.md.
        response.status_code = status.HTTP_200_OK
    return IngestResponse(
        case_id=case.case_id,
        status=case.status,
        created_at=case.occurrence_ingested_at,
        replayed=replayed,
    )
