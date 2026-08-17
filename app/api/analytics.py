"""GET /api/analytics — group-by aggregations over cases.

Day 1: stubbed to 501.
Planned: D5-7 — see docs/api-contract.md section 6.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.stub import not_implemented
from app.db import get_db
from app.schemas.case import AnalyticsResponse

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/analytics", response_model=AnalyticsResponse)
def analytics(
    db: Session = Depends(get_db),
    _from: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    group_by: list[str] = Query(default=["type"]),
) -> AnalyticsResponse:
    not_implemented("D5-7")
