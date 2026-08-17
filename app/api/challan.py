"""POST /api/challan — mock challan generation.

Day 1: stubbed to 501.
Planned: D5-7 — see docs/api-contract.md section 5.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.stub import not_implemented
from app.db import get_db
from app.schemas.case import ChallanRequest, ChallanResponse

router = APIRouter(prefix="/api", tags=["challan"])


@router.post("/challan", response_model=ChallanResponse, status_code=202)
def create_challan(
    payload: ChallanRequest, db: Session = Depends(get_db)
) -> ChallanResponse:
    not_implemented("D5-7")
