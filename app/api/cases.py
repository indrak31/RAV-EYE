"""Case list/detail/review endpoints.

Day 3-5: implemented using case_service.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.case import CaseListResponse, CaseListItem, CaseOut, ReviewRequest
from app.schemas.enums import CaseStatus, ViolationType
from app.services import case_service
from app.services.event_bus import case_reviewed_event, event_bus
from app.services.serialization import case_to_list_item, case_to_out

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("", response_model=CaseListResponse)
def list_cases(
    response: Response,
    status_filter: list[CaseStatus] = Query(default=[], alias="status"),
    camera_id: str | None = Query(default=None),
    violation_type: ViolationType | None = Query(default=None),
    plate: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> CaseListResponse:
    total, cases = case_service.list_cases(
        db,
        status_filter=status_filter if status_filter else None,
        camera_id=camera_id,
        violation_type=violation_type.value if violation_type else None,
        plate=plate,
        limit=limit,
        offset=offset,
    )
    items = [case_to_list_item(c) for c in cases]
    return CaseListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: str, db: Session = Depends(get_db)) -> CaseOut:
    try:
        case = case_service.get_case(db, case_id)
    except case_service.CaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "case_not_found"})

    # Auto-transition ingested -> in_review on first detail view (optional, per open question)
    # case = case_service.transition_to_in_review(db, case_id)

    return case_to_out(case)


@router.patch("/{case_id}/review", response_model=CaseOut)
def review_case(
    case_id: str,
    payload: ReviewRequest,
    db: Session = Depends(get_db),
) -> CaseOut:
    try:
        case = case_service.review_case(db, case_id, payload)
    except case_service.CaseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"detail": "case_not_found"})
    except case_service.CaseNotReviewableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"detail": "case_not_reviewable"})

    # Broadcast case.reviewed event
    event_bus.broadcast_sync("case.reviewed", **case_reviewed_event(
        case_id=case.case_id,
        decision=case.review_decision,
        reviewer_id=case.reviewer_id,
    ))

    return case_to_out(case)