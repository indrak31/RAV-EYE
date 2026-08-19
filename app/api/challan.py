"""POST /api/challan — mock challan generation.

Day 5-7: implemented using case_service.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.case import ChallanRequest, ChallanResponse
from app.schemas.enums import ChallanChannel
from app.services import case_service
from app.services.event_bus import challan_issued_event, event_bus

router = APIRouter(prefix="/api", tags=["challan"])


def _generate_challan_id() -> str:
    """Generate challan ID in format CH-YYYY-NNNNNN."""
    year = datetime.now().year
    random_part = uuid.uuid4().int % 1_000_000
    return f"CH-{year}-{random_part:06d}"


@router.post("/challan", response_model=ChallanResponse, status_code=202)
def create_challan(
    payload: ChallanRequest, db: Session = Depends(get_db)
) -> ChallanResponse:
    try:
        # Verify case exists and is eligible
        case = case_service.get_case(db, payload.case_id)
        if not case_service.is_challan_eligible(case):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"detail": "challan_not_eligible"},
            )

        # Mark case as challan_issued
        case_service.mark_challan_issued(db, payload.case_id)

        # Generate mock challan
        challan_id = _generate_challan_id()

        # Broadcast challan.issued event
        event_bus.broadcast_sync("challan.issued", **challan_issued_event(
            challan_id=challan_id,
            case_id=payload.case_id,
            channel=payload.channel.value,
        ))

        return ChallanResponse(
            challan_id=challan_id,
            case_id=payload.case_id,
            status="queued",
            channel=payload.channel,
        )

    except case_service.CaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "case_not_found"})