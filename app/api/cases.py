"""Case list/detail/review endpoints.

Day 1: stubbed to 501.
Planned: D3-5 — see docs/api-contract.md sections 2-4.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.stub import not_implemented
from app.db import get_db
from app.schemas.case import (
    CaseListResponse,
    CaseOut,
    ReviewRequest,
)
from app.schemas.enums import CaseStatus, ViolationType

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("", response_model=CaseListResponse)
def list_cases(
    status_filter: list[CaseStatus] = Query(default=[], alias="status"),
    camera_id: str | None = Query(default=None),
    violation_type: ViolationType | None = Query(default=None),
    plate: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> CaseListResponse:
    not_implemented("D3-5")


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: str, db: Session = Depends(get_db)) -> CaseOut:
    not_implemented("D3-5")


@router.patch("/{case_id}/review", response_model=CaseOut)
def review_case(
    case_id: str,
    payload: ReviewRequest,
    db: Session = Depends(get_db),
) -> CaseOut:
    not_implemented("D3-5")
