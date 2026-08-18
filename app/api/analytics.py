"""GET /api/analytics — group-by aggregations over cases.

Implements real SQLAlchemy group-by queries for violations by type, camera, hour.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Case
from app.schemas.case import AnalyticsResponse, AnalyticsRow
from app.schemas.enums import ViolationType

router = APIRouter(prefix="/api", tags=["analytics"])


def _parse_date(date_str: str | None) -> datetime | None:
    """Parse ISO date string to UTC datetime."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return None


def _apply_date_filters(stmt, date_from: datetime | None, date_to: datetime | None):
    """Apply date filters to a statement."""
    if date_from:
        stmt = stmt.where(Case.occurrence_occurred_at >= date_from)
    if date_to:
        stmt = stmt.where(Case.occurrence_occurred_at <= date_to)
    return stmt


def _group_by_type(db: Session, date_from: datetime | None, date_to: datetime | None) -> list[AnalyticsRow]:
    """Group by violation_type."""
    stmt = select(Case.violation_type, func.count(Case.case_id))
    stmt = _apply_date_filters(stmt, date_from, date_to)
    stmt = stmt.group_by(Case.violation_type)
    rows = db.execute(stmt).all()
    return [
        AnalyticsRow(violation_type=row[0].value if hasattr(row[0], "value") else row[0], count=row[1])
        for row in rows
    ]


def _group_by_camera(db: Session, date_from: datetime | None, date_to: datetime | None) -> list[AnalyticsRow]:
    """Group by camera_id."""
    stmt = select(Case.camera_id, func.count(Case.case_id))
    stmt = _apply_date_filters(stmt, date_from, date_to)
    stmt = stmt.group_by(Case.camera_id)
    rows = db.execute(stmt).all()
    return [AnalyticsRow(camera_id=row[0], count=row[1]) for row in rows]


def _group_by_hour(db: Session, date_from: datetime | None, date_to: datetime | None) -> list[AnalyticsRow]:
    """Group by hour of occurrence_occurred_at (UTC)."""
    hour_expr = func.strftime("%H", Case.occurrence_occurred_at)
    stmt = select(hour_expr, func.count(Case.case_id))
    stmt = _apply_date_filters(stmt, date_from, date_to)
    stmt = stmt.group_by(hour_expr)
    rows = db.execute(stmt).all()
    return [AnalyticsRow(hour=int(row[0]), count=row[1]) for row in rows]


def _compute_totals(
    db: Session,
    date_from: datetime | None,
    date_to: datetime | None,
    group_by: list[str],
) -> dict[str, dict[str, int]]:
    """Compute totals for each requested grouping dimension."""
    totals: dict[str, dict[str, int]] = {}

    if "type" in group_by:
        type_rows = _group_by_type(db, date_from, date_to)
        totals["by_type"] = {row.violation_type or "unknown": row.count for row in type_rows}

    if "camera" in group_by:
        camera_rows = _group_by_camera(db, date_from, date_to)
        totals["by_camera"] = {row.camera_id or "unknown": row.count for row in camera_rows}

    if "hour" in group_by:
        hour_rows = _group_by_hour(db, date_from, date_to)
        totals["by_hour"] = {str(row.hour).zfill(2): row.count for row in hour_rows}

    return totals


@router.get("/analytics", response_model=AnalyticsResponse)
def analytics(
    db: Session = Depends(get_db),
    _from: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    group_by: list[str] = Query(default=["type"]),
) -> AnalyticsResponse:
    """Aggregate case counts grouped by violation type, camera, and/or hour.

    Query params:
        from: ISO date (inclusive), e.g., 2026-08-01
        to: ISO date (inclusive), e.g., 2026-08-17
        group_by: repeatable, values in ["type", "camera", "hour"]

    Returns:
        AnalyticsResponse with rows and totals.
    """
    # Validate group_by values
    valid_groups = {"type", "camera", "hour"}
    for g in group_by:
        if g not in valid_groups:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"detail": f"invalid group_by value: {g}", "allowed": sorted(valid_groups)},
            )

    date_from = _parse_date(_from)
    date_to = _parse_date(to)

    # Build rows based on group_by
    rows: list[AnalyticsRow] = []
    if "type" in group_by:
        rows.extend(_group_by_type(db, date_from, date_to))
    if "camera" in group_by:
        rows.extend(_group_by_camera(db, date_from, date_to))
    if "hour" in group_by:
        rows.extend(_group_by_hour(db, date_from, date_to))

    totals = _compute_totals(db, date_from, date_to, group_by)

    return AnalyticsResponse(
        from_=_from,
        to=to,
        group_by=group_by,
        rows=rows,
        totals=totals,
    )